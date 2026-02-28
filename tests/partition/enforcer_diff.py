#!/usr/bin/env python3
"""
Specialized diff for enforcer outputs.
Each timestamp has TWO blocks: one reactive and one proactive.
Blocks are matched by (timestamp, type) and compared separately.

Features:
- Parse enforcer output into blocks, preserving reactive/proactive distinction
- Combine multiple blocks at the same timestamp and type (useful for merging partition outputs)
- Compare blocks between reference and partition outputs
- Calculate match percentage and generate detailed diff reports

Block combining logic:
- Only combines blocks of the same type (reactive with reactive, proactive with proactive)
- If one block does nothing but another has events, take the events
- If multiple blocks have events, merge all causes and suppressions
- Duplicates are removed while preserving order
- Always ensures both reactive and proactive blocks exist for each timestamp
"""

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
    
    def __hash__(self):
        return hash((self.timestamp, self.is_reactive))
    
    def __eq__(self, other):
        if not isinstance(other, EnforcerBlock):
            return False
        return self.timestamp == other.timestamp and self.is_reactive == other.is_reactive


def parse_enforcer_output(output: str) -> List[EnforcerBlock]:
    """
    Parse enforcer output into blocks.
    Each timestamp has TWO blocks: one reactive and one proactive.
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
    
    for line in output.split('\n'):
        # Check if this is a label line
        if line.startswith('[Enforcer:Label]'):
            # Buffer this label line for the next [Enforcer] block
            label_buffer.append(line)
        # Check if this is a new [Enforcer] line (but not [Enforcer:Label])
        elif line.startswith('[Enforcer]') and not line.startswith('[Enforcer:Label]'):
            # Save previous block if it exists
            if current_block_lines and current_timestamp is not None and current_is_reactive is not None:
                raw_content = '\n'.join(current_block_lines)
                blocks.append(EnforcerBlock(
                    timestamp=current_timestamp,
                    raw_content=raw_content,
                    lines=current_block_lines.copy(),
                    is_reactive=current_is_reactive
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
        raw_content = '\n'.join(current_block_lines)
        blocks.append(EnforcerBlock(
            timestamp=current_timestamp,
            raw_content=raw_content,
            lines=current_block_lines.copy(),
            is_reactive=current_is_reactive
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
    Combine multiple enforcer blocks with the same timestamp AND type (reactive/proactive).
    All blocks must be of the same type.
    
    Logic:
    - If one block does nothing but another has events, take the events
    - If multiple blocks have events, merge all causes and suppressions
    - Remove duplicates while preserving order
    
    Args:
        blocks: List of EnforcerBlock objects with the same timestamp and type
        
    Returns:
        A single combined EnforcerBlock
    """
    if not blocks:
        raise ValueError("Cannot combine empty list of blocks")
    
    if len(blocks) == 1:
        return blocks[0]
    
    timestamp = blocks[0].timestamp
    is_reactive = blocks[0].is_reactive
    
    # Verify all blocks are of the same type
    if not all(b.is_reactive == is_reactive for b in blocks):
        raise ValueError("Cannot combine blocks of different types (reactive/proactive)")
    
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
        is_reactive=is_reactive
    )


def combine_blocks_by_timestamp(blocks: List[EnforcerBlock]) -> List[EnforcerBlock]:
    """
    Combine multiple blocks that share the same timestamp and type.
    Only combines blocks that actually exist in the input - does not create missing blocks.
    Typically each timestamp has TWO blocks (reactive + proactive), but the last timestamp
    may only have a reactive block.
    
    Args:
        blocks: List of EnforcerBlock objects (may have duplicate timestamps)
        
    Returns:
        List of combined EnforcerBlock objects sorted by (timestamp, is_reactive)
    """
    # Group blocks by (timestamp, is_reactive)
    groups: Dict[Tuple[int, bool], List[EnforcerBlock]] = {}
    
    for block in blocks:
        key = (block.timestamp, block.is_reactive)
        if key not in groups:
            groups[key] = []
        groups[key].append(block)
    
    # Combine each group and return sorted results
    combined_blocks = []
    for key in sorted(groups.keys()):
        combined = combine_blocks(groups[key])
        combined_blocks.append(combined)
    
    return combined_blocks


def compare_blocks(ref_block: EnforcerBlock, part_block: EnforcerBlock) -> Tuple[bool, List[str]]:
    """
    Compare two blocks with the same timestamp.
    Actions are compared as sets (order doesn't matter).
    Labels are compared as sets (order doesn't matter).
    
    Args:
        ref_block: Reference block
        part_block: Partition block
        
    Returns:
        Tuple of (matches: bool, differences: List[str])
    """
    differences = []
    
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
    
    if not (causes_match and suppressions_match and labels_match):
        differences.append("  REFERENCE:")
        for line in ref_block.lines:
            differences.append(f"    {line}")
        differences.append("")
        differences.append("  PARTITION:")
        for line in part_block.lines:
            differences.append(f"    {line}")
        differences.append("")
        
        # Show what differs
        if not labels_match:
            differences.append("  Labels differ:")
            only_ref = ref_labels_set - part_labels_set
            only_part = part_labels_set - ref_labels_set
            if only_ref:
                differences.append(f"    Only in reference ({len(only_ref)} labels):")
                for label in sorted(only_ref):
                    differences.append(f"      {label}")
            if only_part:
                differences.append(f"    Only in partition ({len(only_part)} labels):")
                for label in sorted(only_part):
                    differences.append(f"      {label}")
        
        if not causes_match:
            differences.append("  Causes differ:")
            only_ref = ref_causes_set - part_causes_set
            only_part = part_causes_set - ref_causes_set
            if only_ref:
                differences.append(f"    Only in reference: {sorted(only_ref)}")
            if only_part:
                differences.append(f"    Only in partition: {sorted(only_part)}")
        
        if not suppressions_match:
            differences.append("  Suppressions differ:")
            only_ref = ref_suppressions_set - part_suppressions_set
            only_part = part_suppressions_set - ref_suppressions_set
            if only_ref:
                differences.append(f"    Only in reference: {sorted(only_ref)}")
            if only_part:
                differences.append(f"    Only in partition: {sorted(only_part)}")
    
    matches = len(differences) == 0
    return matches, differences


def compare_enforcer_outputs(reference_output: str, partition_output: str, partition_name: str = "partition") -> Dict:
    """
    Compare two enforcer outputs block by block.
    Each timestamp has TWO blocks (reactive and proactive) that are compared separately.
    
    Args:
        reference_output: Reference enforcer output
        partition_output: Partition enforcer output
        partition_name: Name of partition for reporting
        
    Returns:
        Dictionary with comparison results including:
        - total_blocks: Total number of blocks (2 per timestamp: reactive + proactive)
        - matching_blocks: Number of matching blocks
        - differing_blocks: Number of differing blocks
        - missing_in_partition: List of (timestamp, block_type) tuples missing in partition
        - extra_in_partition: List of (timestamp, block_type) tuples extra in partition
        - match_percentage: Percentage of matching blocks
        - block_differences: Dict mapping (timestamp, is_reactive) to diff info
    """
    # Parse both outputs
    ref_blocks = parse_enforcer_output(reference_output)
    part_blocks = parse_enforcer_output(partition_output)
    
    # Create (timestamp, is_reactive)-indexed dictionaries
    # Each timestamp has TWO blocks: one reactive and one proactive
    ref_dict = {(block.timestamp, block.is_reactive): block for block in ref_blocks}
    part_dict = {(block.timestamp, block.is_reactive): block for block in part_blocks}
    
    # Find all unique (timestamp, is_reactive) keys
    all_block_keys = sorted(set(ref_dict.keys()) | set(part_dict.keys()))
    
    # Compare blocks
    matching_blocks = 0
    differing_blocks = 0
    missing_in_partition = []
    extra_in_partition = []
    block_differences = {}
    
    for key in all_block_keys:
        ts, is_reactive = key
        ref_block = ref_dict.get(key)
        part_block = part_dict.get(key)
        
        block_type = "reactive" if is_reactive else "proactive"
        
        if ref_block and part_block:
            # Both have this block - compare them
            matches, diffs = compare_blocks(ref_block, part_block)
            if matches:
                matching_blocks += 1
            else:
                differing_blocks += 1
                block_differences[key] = {
                    'type': block_type,
                    'diffs': diffs
                }
        elif ref_block and not part_block:
            # Missing in partition
            missing_in_partition.append((ts, block_type))
        elif part_block and not ref_block:
            # Extra in partition
            extra_in_partition.append((ts, block_type))
    
    total_blocks = len(all_block_keys)
    match_percentage = (matching_blocks / total_blocks * 100) if total_blocks > 0 else 0.0
    
    return {
        'total_blocks': total_blocks,
        'matching_blocks': matching_blocks,
        'differing_blocks': differing_blocks,
        'missing_in_partition': missing_in_partition,
        'extra_in_partition': extra_in_partition,
        'match_percentage': match_percentage,
        'block_differences': block_differences,
        'partition_name': partition_name
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
    
    lines.append("SUMMARY:")
    lines.append(f"  Total blocks: {comparison['total_blocks']}")
    lines.append(f"  Matching blocks: {comparison['matching_blocks']}")
    lines.append(f"  Differing blocks: {comparison['differing_blocks']}")
    lines.append(f"  Match percentage: {comparison['match_percentage']:.2f}%")
    lines.append("")
    
    if comparison['missing_in_partition']:
        lines.append(f"MISSING IN PARTITION ({len(comparison['missing_in_partition'])} blocks):")
        for ts, block_type in comparison['missing_in_partition'][:10]:  # Show first 10
            lines.append(f"  @{ts} ({block_type})")
        if len(comparison['missing_in_partition']) > 10:
            lines.append(f"  ... and {len(comparison['missing_in_partition']) - 10} more")
        lines.append("")
    
    if comparison['extra_in_partition']:
        lines.append(f"EXTRA IN PARTITION ({len(comparison['extra_in_partition'])} blocks):")
        for ts, block_type in comparison['extra_in_partition'][:10]:  # Show first 10
            lines.append(f"  @{ts} ({block_type})")
        if len(comparison['extra_in_partition']) > 10:
            lines.append(f"  ... and {len(comparison['extra_in_partition']) - 10} more")
        lines.append("")
    
    if comparison['block_differences']:
        lines.append(f"DIFFERING BLOCKS ({len(comparison['block_differences'])} blocks):")
        lines.append("")
        
        # Show details for each differing block (limit to first 20)
        for i, (key, diff_info) in enumerate(list(comparison['block_differences'].items())[:20]):
            ts, is_reactive = key
            block_type = diff_info['type']
            diffs = diff_info['diffs']
            lines.append(f"Block @{ts} ({block_type}):")
            lines.extend(diffs)
            lines.append("")
            
        if len(comparison['block_differences']) > 20:
            lines.append(f"... and {len(comparison['block_differences']) - 20} more differing blocks")
            lines.append("")
    
    return '\n'.join(lines)


def save_comparison_report(comparison: Dict, output_file: str):
    """
    Save comparison report to file.
    
    Args:
        comparison: Results from compare_enforcer_outputs
        output_file: Path to output file
    """
    report = format_comparison_report(comparison)
    with open(output_file, 'w') as f:
        f.write(report)
