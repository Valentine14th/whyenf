#!/usr/bin/env python3
"""
Specialized diff for enforcer outputs.
Each timestamp may have reactive and/or proactive blocks.
Blocks are matched by (timestamp, type) and compared separately.

Features:
- Parse enforcer output into blocks, preserving reactive/proactive distinction
- Combine multiple blocks at the same timestamp and type (useful for merging partition outputs)
- Compare blocks between reference and partition outputs
- Calculate match percentage and generate detailed diff reports (plaintext and JSON)

Block combining logic:
- Only combines blocks of the same type (reactive with reactive, proactive with proactive)
- If one block does nothing but another has events, take the events
- If multiple blocks have events, merge all causes and suppressions
- Duplicates are removed while preserving order
- Only combines blocks that actually exist in the input
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class EnforcerBlock:
    """Represents a single [Enforcer] block."""
    timestamp: int
    raw_content: str
    lines: List[str]
    is_reactive: bool  # True for reactive, False for proactive
    block_index: int = 0  # Index within (timestamp, type) - for handling multiple blocks of same type at same timestamp
    
    def __hash__(self):
        return hash((self.timestamp, self.is_reactive, self.block_index))
    
    def __eq__(self, other):
        if not isinstance(other, EnforcerBlock):
            return False
        return self.timestamp == other.timestamp and self.is_reactive == other.is_reactive and self.block_index == other.block_index


def parse_enforcer_output(output: str) -> List[EnforcerBlock]:
    """
    Parse enforcer output into blocks.
    Each timestamp may have 0, 1, or multiple blocks of each type (reactive and/or proactive).
    Block indices are assigned based on the order blocks appear for each (timestamp, type).
    Label lines ([Enforcer:Label]) that precede an [Enforcer] block are included in that block.
    
    Args:
        output: Raw enforcer output string
        
    Returns:
        List of EnforcerBlock objects
    """
    blocks = []
    current_block_lines = []
    current_timestamp = None
    current_is_reactive = None
    label_buffer = []  # Buffer for [Enforcer:Label] lines before next [Enforcer] block
    block_counters = {}  # Track block count per (timestamp, is_reactive)
    
    for line in output.split('\n'):
        # Check if this is a label line
        if line.startswith('[Enforcer:Label]'):
            # Buffer this label line for the next [Enforcer] block
            label_buffer.append(line)
        # Check if this is a new [Enforcer] line (but not [Enforcer:Label])
        elif line.startswith('[Enforcer]') and not line.startswith('[Enforcer:Label]'):
            # Save previous block if it exists
            if current_block_lines and current_timestamp is not None and current_is_reactive is not None:
                # Determine block index
                key = (current_timestamp, current_is_reactive)
                block_index = block_counters.get(key, 0)
                block_counters[key] = block_index + 1
                
                raw_content = '\n'.join(current_block_lines)
                blocks.append(EnforcerBlock(
                    timestamp=current_timestamp,
                    raw_content=raw_content,
                    lines=current_block_lines.copy(),
                    is_reactive=current_is_reactive,
                    block_index=block_index
                ))
            
            # Start new block with buffered labels plus this line
            current_block_lines = label_buffer + [line]
            label_buffer = []  # Clear label buffer
            
            # Extract timestamp from this line
            # Format: [Enforcer] @timestamp ...
            match = re.search(r'@(\d+)', line)
            if match:
                current_timestamp = int(match.group(1))
            else:
                current_timestamp = None
            
            # Determine if reactive or proactive
            if 'reactively commands' in line or (line.endswith('OK.') and 'proactively' not in line):
                current_is_reactive = True
            elif 'proactively commands' in line or 'nothing to do proactively' in line:
                current_is_reactive = False
            else:
                current_is_reactive = None
        else:
            # Continue current block (only if we're in a block)
            if current_timestamp is not None:
                current_block_lines.append(line)
            # If current_timestamp is None, we're before the first block, so ignore
    
    # Don't forget the last block
    if current_block_lines and current_timestamp is not None and current_is_reactive is not None:
        # Determine block index
        key = (current_timestamp, current_is_reactive)
        block_index = block_counters.get(key, 0)
        block_counters[key] = block_index + 1
        
        raw_content = '\n'.join(current_block_lines)
        blocks.append(EnforcerBlock(
            timestamp=current_timestamp,
            raw_content=raw_content,
            lines=current_block_lines.copy(),
            is_reactive=current_is_reactive,
            block_index=block_index
        ))
    
    return blocks


def parse_actions_line(line: str) -> List[str]:
    """
    Parse a line containing comma-separated actions.
    Actions have the form Name(...) where ... can contain commas.
    Only split by commas that are outside parentheses.
    
    Args:
        line: String containing comma-separated actions
        
    Returns:
        List of individual actions
    """
    actions = []
    current_action = []
    paren_depth = 0
    
    for char in line:
        if char == '(':
            paren_depth += 1
            current_action.append(char)
        elif char == ')':
            paren_depth -= 1
            current_action.append(char)
        elif char == ',' and paren_depth == 0:
            # This comma is a separator between actions
            action = ''.join(current_action).strip()
            if action:
                actions.append(action)
            current_action = []
        else:
            current_action.append(char)
    
    # Don't forget the last action
    action = ''.join(current_action).strip()
    if action:
        actions.append(action)
    
    return actions


def parse_block_actions(block: EnforcerBlock) -> Tuple[List[str], List[str]]:
    """
    Parse an enforcer block to extract causes and suppressions.
    Actions are comma-separated on a single line after Cause:/Suppress:.
    Actions have the form Name(...) where ... can contain commas.
    
    Args:
        block: EnforcerBlock to parse
        
    Returns:
        Tuple of (causes, suppressions)
        - causes: List of individual caused events
        - suppressions: List of individual suppressed events
    """
    causes = []
    suppressions = []
    
    in_cause_section = False
    in_suppress_section = False
    
    for line in block.lines:
        line = line.strip()
        
        if line == 'Cause:':
            in_cause_section = True
            in_suppress_section = False
        elif line == 'Suppress:':
            in_cause_section = False
            in_suppress_section = True
        elif line in ['OK.', 'nothing to do proactively.', '']:
            in_cause_section = False
            in_suppress_section = False
        elif in_cause_section and line and not line.startswith('[Enforcer'):
            # Parse comma-separated actions respecting parentheses
            actions = parse_actions_line(line)
            causes.extend(actions)
        elif in_suppress_section and line and not line.startswith('[Enforcer'):
            # Parse comma-separated actions respecting parentheses
            actions = parse_actions_line(line)
            suppressions.extend(actions)
    
    return causes, suppressions


def combine_blocks(blocks: List[EnforcerBlock]) -> EnforcerBlock:
    """
    Combine multiple enforcer blocks with the same timestamp, type, AND block_index.
    All blocks must have the same timestamp, type, and block_index (from different partitions).
    
    Logic:
    - If one block does nothing but another has events, take the events
    - If multiple blocks have events, merge all causes and suppressions
    - Remove duplicates while preserving order
    
    Args:
        blocks: List of EnforcerBlock objects with the same timestamp, type, and block_index
        
    Returns:
        A single combined EnforcerBlock
    """
    if not blocks:
        raise ValueError("Cannot combine empty list of blocks")
    
    if len(blocks) == 1:
        return blocks[0]
    
    timestamp = blocks[0].timestamp
    is_reactive = blocks[0].is_reactive
    block_index = blocks[0].block_index
    
    # Verify all blocks have the same timestamp, type, and block_index
    if not all(b.timestamp == timestamp and b.is_reactive == is_reactive and b.block_index == block_index for b in blocks):
        raise ValueError("Cannot combine blocks with different timestamp, type, or block_index")
    
    # Collect all label lines from all blocks (they should appear before the [Enforcer] line)
    all_label_lines = []
    for block in blocks:
        for line in block.lines:
            if line.startswith('[Enforcer:Label]'):
                if line not in all_label_lines:
                    all_label_lines.append(line)
    
    # Parse all blocks
    all_causes = []
    all_suppressions = []
    
    for block in blocks:
        causes, suppressions = parse_block_actions(block)
        
        # Add causes (avoid duplicates while preserving order)
        for cause in causes:
            if cause not in all_causes:
                all_causes.append(cause)
        
        # Add suppressions (avoid duplicates while preserving order)
        for suppress in suppressions:
            if suppress not in all_suppressions:
                all_suppressions.append(suppress)
    
    # Generate combined block content
    lines = []
    
    # Add label lines first
    lines.extend(all_label_lines)
    
    if all_causes or all_suppressions:
        # Has actions to perform
        if is_reactive:
            lines.append(f"[Enforcer] @{timestamp} reactively commands:")
        else:
            lines.append(f"[Enforcer] @{timestamp} proactively commands:")
        
        if all_causes:
            lines.append("Cause:")
            # Merge all causes on one line, comma-separated
            lines.append(", ".join(all_causes))
        
        if all_suppressions:
            lines.append("Suppress:")
            # Merge all suppressions on one line, comma-separated
            lines.append(", ".join(all_suppressions))
        
        lines.append("OK.")
    else:
        # Nothing to do
        if is_reactive:
            lines.append(f"[Enforcer] @{timestamp} OK.")
        else:
            lines.append(f"[Enforcer] @{timestamp} nothing to do proactively.")
    
    raw_content = '\n'.join(lines)
    
    return EnforcerBlock(
        timestamp=timestamp,
        raw_content=raw_content,
        lines=lines,
        is_reactive=is_reactive,
        block_index=block_index
    )


def combine_blocks_by_timestamp(blocks: List[EnforcerBlock]) -> List[EnforcerBlock]:
    """
    Combine multiple blocks that share the same timestamp, type, and block_index.
    Only combines blocks that actually exist in the input - does not create missing blocks.
    Each timestamp may have 0, 1, or multiple blocks of each type (reactive/proactive).
    Blocks are aligned by their block_index across partitions.
    
    Args:
        blocks: List of EnforcerBlock objects (may have duplicate timestamps)
        
    Returns:
        List of combined EnforcerBlock objects sorted by (timestamp, is_reactive, block_index)
    """
    # Group blocks by (timestamp, is_reactive, block_index)
    groups: Dict[Tuple[int, bool, int], List[EnforcerBlock]] = {}
    
    for block in blocks:
        key = (block.timestamp, block.is_reactive, block.block_index)
        if key not in groups:
            groups[key] = []
        groups[key].append(block)
    
    # Combine each group and return sorted results
    combined_blocks = []
    for key in sorted(groups.keys()):
        combined = combine_blocks(groups[key])
        combined_blocks.append(combined)
    
    return combined_blocks


def compare_blocks(ref_block: EnforcerBlock, part_block: EnforcerBlock) -> Tuple[bool, Optional[Dict]]:
    """
    Compare two blocks with the same timestamp.
    Actions are compared as sets (order doesn't matter).
    Labels are compared as sets (order doesn't matter).
    
    Args:
        ref_block: Reference block
        part_block: Partition block
        
    Returns:
        Tuple of (matches: bool, diff_dict: Optional[Dict])
        diff_dict contains structured information about differences
    """
    # Parse actions from both blocks
    ref_causes, ref_suppressions = parse_block_actions(ref_block)
    part_causes, part_suppressions = parse_block_actions(part_block)
    
    # Extract labels from both blocks (lines starting with [Enforcer:Label])
    ref_labels = [line for line in ref_block.lines if line.startswith('[Enforcer:Label]')]
    part_labels = [line for line in part_block.lines if line.startswith('[Enforcer:Label]')]
    
    # Compare as sets (order doesn't matter)
    ref_causes_set = set(ref_causes)
    part_causes_set = set(part_causes)
    ref_suppressions_set = set(ref_suppressions)
    part_suppressions_set = set(part_suppressions)
    ref_labels_set = set(ref_labels)
    part_labels_set = set(part_labels)
    
    # Check if they match
    causes_match = ref_causes_set == part_causes_set
    suppressions_match = ref_suppressions_set == part_suppressions_set
    labels_match = ref_labels_set == part_labels_set
    
    matches = causes_match and suppressions_match and labels_match
    
    if not matches:
        # Create structured diff data
        diff_dict = {
            "reference_block": {
                "labels": ref_labels,
                "causes": ref_causes,
                "suppressions": ref_suppressions
            },
            "partition_block": {
                "labels": part_labels,
                "causes": part_causes,
                "suppressions": part_suppressions
            },
            "differences": {
                "labels": {
                    "only_in_reference": sorted(list(ref_labels_set - part_labels_set)),
                    "only_in_partition": sorted(list(part_labels_set - ref_labels_set))
                },
                "causes": {
                    "only_in_reference": sorted(list(ref_causes_set - part_causes_set)),
                    "only_in_partition": sorted(list(part_causes_set - ref_causes_set))
                },
                "suppressions": {
                    "only_in_reference": sorted(list(ref_suppressions_set - part_suppressions_set)),
                    "only_in_partition": sorted(list(part_suppressions_set - ref_suppressions_set))
                }
            }
        }
        return False, diff_dict
    
    return True, None


def compare_enforcer_outputs(reference_output: str, partition_output: str, partition_name: str = "partition") -> Dict:
    """
    Compare two enforcer outputs block by block.
    Each timestamp may have multiple blocks of each type that are compared separately.
    Blocks are matched by (timestamp, type, block_index).
    
    Args:
        reference_output: Reference enforcer output
        partition_output: Partition enforcer output
        partition_name: Name of partition for reporting
        
    Returns:
        Dictionary with comparison results including:
        - total_blocks: Total number of unique (timestamp, block_type, block_index) tuples across both outputs
        - matching_blocks: Number of matching blocks
        - differing_blocks: Number of differing blocks
        - missing_in_partition: List of dicts with timestamp, block_type, and block_index
        - extra_in_partition: List of dicts with timestamp, block_type, and block_index
        - match_percentage: Percentage of matching blocks
        - differing_blocks_details: List of dicts with detailed diff info
    """
    # Parse both outputs
    ref_blocks = parse_enforcer_output(reference_output)
    part_blocks = parse_enforcer_output(partition_output)
    
    # Create (timestamp, is_reactive, block_index)-indexed dictionaries
    # Each timestamp may have multiple blocks of each type
    ref_dict = {(block.timestamp, block.is_reactive, block.block_index): block for block in ref_blocks}
    part_dict = {(block.timestamp, block.is_reactive, block.block_index): block for block in part_blocks}
    
    # Find all unique (timestamp, is_reactive, block_index) keys
    all_block_keys = sorted(set(ref_dict.keys()) | set(part_dict.keys()))
    
    # Compare blocks
    matching_blocks = 0
    differing_blocks_count = 0
    missing_in_partition = []
    extra_in_partition = []
    differing_blocks_details = []
    
    for key in all_block_keys:
        ts, is_reactive, block_index = key
        ref_block = ref_dict.get(key)
        part_block = part_dict.get(key)
        
        block_type = "reactive" if is_reactive else "proactive"
        
        if ref_block and part_block:
            # Both have this block - compare them
            matches, diff_dict = compare_blocks(ref_block, part_block)
            if matches:
                matching_blocks += 1
            else:
                differing_blocks_count += 1
                diff_entry = {
                    "timestamp": ts,
                    "block_type": block_type,
                    "block_index": block_index,
                    "reference_block": diff_dict["reference_block"],
                    "partition_block": diff_dict["partition_block"],
                    "differences": diff_dict["differences"]
                }
                differing_blocks_details.append(diff_entry)
        elif ref_block and not part_block:
            # Missing in partition
            missing_in_partition.append({
                "timestamp": ts,
                "block_type": block_type,
                "block_index": block_index
            })
        elif part_block and not ref_block:
            # Extra in partition
            extra_in_partition.append({
                "timestamp": ts,
                "block_type": block_type,
                "block_index": block_index
            })
    
    total_blocks = len(all_block_keys)
    match_percentage = (matching_blocks / total_blocks * 100) if total_blocks > 0 else 0.0
    
    return {
        'partition_name': partition_name,
        'summary': {
            'total_blocks': total_blocks,
            'matching_blocks': matching_blocks,
            'differing_blocks': differing_blocks_count,
            'match_percentage': match_percentage
        },
        'missing_in_partition': missing_in_partition,
        'extra_in_partition': extra_in_partition,
        'differing_blocks': differing_blocks_details
    }


def format_comparison_report(comparison: Dict) -> str:
    """
    Format comparison results as a readable report.
    
    Args:
        comparison: Results from compare_enforcer_outputs
        
    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"ENFORCER OUTPUT COMPARISON: {comparison['partition_name']}")
    lines.append("=" * 80)
    lines.append("")
    
    summary = comparison['summary']
    lines.append("SUMMARY:")
    lines.append(f"  Total blocks: {summary['total_blocks']}")
    lines.append(f"  Matching blocks: {summary['matching_blocks']}")
    lines.append(f"  Differing blocks: {summary['differing_blocks']}")
    lines.append(f"  Match percentage: {summary['match_percentage']:.2f}%")
    lines.append("")
    
    if comparison['missing_in_partition']:
        lines.append(f"MISSING IN PARTITION ({len(comparison['missing_in_partition'])} blocks):")
        for entry in comparison['missing_in_partition'][:10]:  # Show first 10
            lines.append(f"  @{entry['timestamp']} ({entry['block_type']}, index={entry['block_index']})")
        if len(comparison['missing_in_partition']) > 10:
            lines.append(f"  ... and {len(comparison['missing_in_partition']) - 10} more")
        lines.append("")
    
    if comparison['extra_in_partition']:
        lines.append(f"EXTRA IN PARTITION ({len(comparison['extra_in_partition'])} blocks):")
        for entry in comparison['extra_in_partition'][:10]:  # Show first 10
            lines.append(f"  @{entry['timestamp']} ({entry['block_type']}, index={entry['block_index']})")
        if len(comparison['extra_in_partition']) > 10:
            lines.append(f"  ... and {len(comparison['extra_in_partition']) - 10} more")
        lines.append("")
    
    if comparison['differing_blocks']:
        lines.append(f"DIFFERING BLOCKS ({len(comparison['differing_blocks'])} blocks):")
        lines.append("")
        
        # Show details for each differing block (limit to first 20)
        for diff_entry in comparison['differing_blocks'][:20]:
            ts = diff_entry['timestamp']
            block_type = diff_entry['block_type']
            block_index = diff_entry['block_index']
            ref_block = diff_entry['reference_block']
            part_block = diff_entry['partition_block']
            diffs = diff_entry['differences']
            
            lines.append(f"Block @{ts} ({block_type}, index={block_index}):")
            lines.append("  REFERENCE:")
            lines.append(f"    Labels: {len(ref_block['labels'])}")
            lines.append(f"    Causes: {ref_block['causes']}")
            lines.append(f"    Suppressions: {ref_block['suppressions']}")
            lines.append("")
            lines.append("  PARTITION:")
            lines.append(f"    Labels: {len(part_block['labels'])}")
            lines.append(f"    Causes: {part_block['causes']}")
            lines.append(f"    Suppressions: {part_block['suppressions']}")
            lines.append("")
            
            # Show differences
            if diffs['labels']['only_in_reference'] or diffs['labels']['only_in_partition']:
                lines.append("  Labels differ:")
                if diffs['labels']['only_in_reference']:
                    lines.append(f"    Only in reference: {len(diffs['labels']['only_in_reference'])} labels")
                if diffs['labels']['only_in_partition']:
                    lines.append(f"    Only in partition: {len(diffs['labels']['only_in_partition'])} labels")
            
            if diffs['causes']['only_in_reference'] or diffs['causes']['only_in_partition']:
                lines.append("  Causes differ:")
                if diffs['causes']['only_in_reference']:
                    lines.append(f"    Only in reference: {diffs['causes']['only_in_reference']}")
                if diffs['causes']['only_in_partition']:
                    lines.append(f"    Only in partition: {diffs['causes']['only_in_partition']}")
            
            if diffs['suppressions']['only_in_reference'] or diffs['suppressions']['only_in_partition']:
                lines.append("  Suppressions differ:")
                if diffs['suppressions']['only_in_reference']:
                    lines.append(f"    Only in reference: {diffs['suppressions']['only_in_reference']}")
                if diffs['suppressions']['only_in_partition']:
                    lines.append(f"    Only in partition: {diffs['suppressions']['only_in_partition']}")
            
            lines.append("")
            
        if len(comparison['differing_blocks']) > 20:
            lines.append(f"... and {len(comparison['differing_blocks']) - 20} more differing blocks")
            lines.append("")
    
    return '\n'.join(lines)


def save_comparison_report(comparison: Dict, output_file: str):
    """
    Save comparison report to file (plaintext format).
    
    Args:
        comparison: Results from compare_enforcer_outputs
        output_file: Path to output file
    """
    report = format_comparison_report(comparison)
    with open(output_file, 'w') as f:
        f.write(report)


def save_comparison_json(comparison: Dict, output_file: str):
    """
    Save comparison results as JSON.
    
    Args:
        comparison: Results from compare_enforcer_outputs
        output_file: Path to output JSON file
    """
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2)
