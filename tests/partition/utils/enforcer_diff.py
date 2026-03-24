#!/usr/bin/env python3
"""
Specialized diff for enforcer outputs using timepoint-based block identification.

Each block is uniquely identified by its timepoint (sequential counter 0, 1, 2, ...).
Timestamps are preserved for labeling/debugging but not used for matching.

Features:
- Parse enforcer output into blocks with sequential timepoint assignment
- Save blocks as structured JSON for easy inspection and comparison
- Include timing information in JSON for step-by-step execution
- Combine multiple blocks at the same timepoint and type (for merging partition outputs)
- Compare blocks using timepoint-based matching
- Calculate match percentage and generate detailed diff reports (JSON)

Timepoint assignment:
- Step-by-step execution: Each log line → one block → timepoint from execution (0, 1, 2, ...)
- Batch execution: Parse output → blocks assigned timepoints sequentially (0, 1, 2, ...)

Block combining logic (for partition merging):
- Only combines blocks of the same type (reactive with reactive, proactive with proactive)
- Uses timepoint for matching (primary and only identifier)
- If one block does nothing but another has events, take the events
- If multiple blocks have events, merge all causes and suppressions
- Duplicates are removed while preserving order
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict


def parse_actions_line(line: str) -> List[str]:
    """
    Parse a line containing comma-separated actions.
    Actions have the form Name(...) where ... can contain commas.
    Only split by commas that are outside parentheses.
    """
    actions = []
    current_action = []
    paren_depth = 0
    
    for char in line:
        if char == '(':
            paren_depth += 1
        elif char == ')':
            paren_depth -= 1
        elif char == ',' and paren_depth == 0:
            action = ''.join(current_action).strip()
            if action:
                actions.append(action)
            current_action = []
            continue
        current_action.append(char)
    
    # Last action
    action = ''.join(current_action).strip()
    if action:
        actions.append(action)
    
    return actions


def unique_ordered(items: List[str]) -> List[str]:
    """Return unique items from list preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


@dataclass
class EnforcerBlock:
    """Represents a single [Enforcer] block with sequential timepoint identifier."""
    timestamp: int
    raw_content: str
    lines: List[str]
    block_type: str  # "reactive" or "proactive"
    has_action: bool  # True if block has causes/suppressions
    timepoint: Optional[int] = None  # Sequential counter (0, 1, 2, ...)
    
    def __hash__(self):
        return hash(self.timepoint)
    
    def __eq__(self, other):
        if not isinstance(other, EnforcerBlock):
            return False
        return self.timepoint == other.timepoint
    
    @staticmethod
    def create_block(block_lines: List[str], timestamp: int, block_type: str, timepoint: int) -> 'EnforcerBlock':
        """Create EnforcerBlock from parsed lines."""
        raw_content = '\n'.join(block_lines)
        has_action = 'Cause:' in raw_content or 'Suppress:' in raw_content
        return EnforcerBlock(
            timestamp=timestamp,
            raw_content=raw_content,
            lines=block_lines.copy(),
            block_type=block_type,
            has_action=has_action,
            timepoint=timepoint
        )
    
    def to_dict(self, timing_info: Optional[Dict] = None) -> Dict:
        """Convert block to JSON-serializable dictionary."""
        causes, suppressions = parse_block_actions(self)
        
        result = {
            'timepoint': self.timepoint,
            'timestamp': self.timestamp,
            'block_type': self.block_type,
            'has_action': self.has_action,
            'causes': causes,
            'suppressions': suppressions,
            'raw_content': self.raw_content
        }
        
        if timing_info:
            if 'step_time' in timing_info:
                result['time'] = timing_info['step_time']
            if 'cumulative_time' in timing_info:
                result['cumulative_time'] = timing_info['cumulative_time']
        
        return result
    
    @staticmethod
    def from_dict(data: Dict) -> 'EnforcerBlock':
        """Create EnforcerBlock from dictionary."""
        return EnforcerBlock(
            timestamp=data['timestamp'],
            raw_content=data['raw_content'],
            lines=data['raw_content'].split('\n'),
            block_type=data['block_type'],
            has_action=data['has_action'],
            timepoint=data['timepoint']
        )


def parse_enforcer_output(output: str) -> List[EnforcerBlock]:
    """Parse enforcer output into blocks and assign sequential timepoints."""
    blocks = []
    current_block_lines = []
    current_timestamp = None
    current_block_type = None
    label_buffer = []
    
    def save_current_block():
        """Save the current block if it's valid."""
        if current_block_lines and current_timestamp is not None and current_block_type is not None:
            blocks.append(EnforcerBlock.create_block(
                current_block_lines, current_timestamp, current_block_type, len(blocks)
            ))
    
    for line in output.split('\n'):
        if line.startswith('[Enforcer:Label]'):
            label_buffer.append(line)
        elif line.startswith('[Enforcer]') and not line.startswith('[Enforcer:Label]'):
            save_current_block()
            
            # Start new block
            current_block_lines = label_buffer + [line]
            label_buffer = []
            
            # Extract timestamp
            match = re.search(r'@(\d+)', line)
            current_timestamp = int(match.group(1)) if match else None
            
            # Determine block type
            if 'reactively commands' in line or (line.endswith('OK.') and 'proactively' not in line):
                current_block_type = 'reactive'
            elif 'proactively commands' in line or 'nothing to do proactively' in line:
                current_block_type = 'proactive'
            else:
                current_block_type = None
        elif current_timestamp is not None:
            current_block_lines.append(line)
    
    save_current_block()
    return blocks


def parse_block_actions(block: EnforcerBlock) -> Tuple[List[str], List[str]]:
    """Parse an enforcer block to extract causes and suppressions."""
    causes = []
    suppressions = []
    in_cause_section = False
    in_suppress_section = False
    
    for line in block.lines:
        line = line.strip()
        
        if line == 'Cause:':
            in_cause_section, in_suppress_section = True, False
        elif line == 'Suppress:':
            in_cause_section, in_suppress_section = False, True
        elif line in ['OK.', 'nothing to do proactively.', '']:
            in_cause_section, in_suppress_section = False, False
        elif line and not line.startswith('[Enforcer'):
            if in_cause_section:
                causes.extend(parse_actions_line(line))
            elif in_suppress_section:
                suppressions.extend(parse_actions_line(line))
    
    return causes, suppressions


def combine_blocks(blocks: List[EnforcerBlock]) -> EnforcerBlock:
    """Combine multiple enforcer blocks with the same timepoint."""
    if not blocks:
        raise ValueError("Cannot combine empty list of blocks")
    if len(blocks) == 1:
        return blocks[0]
    
    timestamp, block_type, timepoint = blocks[0].timestamp, blocks[0].block_type, blocks[0].timepoint
    
    if not all(b.timepoint == timepoint for b in blocks):
        raise ValueError("Cannot combine blocks with different timepoints")
    
    # Collect unique label lines
    all_label_lines = unique_ordered([
        line for block in blocks for line in block.lines 
        if line.startswith('[Enforcer:Label]')
    ])
    
    # Parse and merge all causes and suppressions
    all_causes, all_suppressions = [], []
    for block in blocks:
        causes, suppressions = parse_block_actions(block)
        all_causes.extend(causes)
        all_suppressions.extend(suppressions)
    
    all_causes = unique_ordered(all_causes)
    all_suppressions = unique_ordered(all_suppressions)
    
    # Build combined block content
    lines = list(all_label_lines)
    
    if all_causes or all_suppressions:
        cmd = 'reactively commands:' if block_type == 'reactive' else 'proactively commands:'
        lines.append(f"[Enforcer] @{timestamp} {cmd}")
        
        if all_causes:
            lines.extend(['Cause:', ", ".join(all_causes)])
        if all_suppressions:
            lines.extend(['Suppress:', ", ".join(all_suppressions)])
        
        lines.append("OK.")
    else:
        suffix = 'OK.' if block_type == 'reactive' else 'nothing to do proactively.'
        lines.append(f"[Enforcer] @{timestamp} {suffix}")
    
    return EnforcerBlock(
        timestamp=timestamp,
        raw_content='\n'.join(lines),
        lines=lines,
        block_type=block_type,
        has_action=bool(all_causes or all_suppressions),
        timepoint=timepoint
    )


def combine_blocks_by_timepoint(blocks: List[EnforcerBlock]) -> List[EnforcerBlock]:
    """Combine multiple blocks that share the same timepoint."""
    groups = defaultdict(list)
    
    for block in blocks:
        if block.timepoint is None:
            raise ValueError(f"Block at timestamp {block.timestamp} has no timepoint assigned")
        groups[block.timepoint].append(block)
    
    return [combine_blocks(groups[key]) for key in sorted(groups.keys())]


def compare_lists(ref_list: List[str], part_list: List[str]) -> Tuple[bool, List[str], List[str]]:
    """Compare two lists as sets and return differences."""
    ref_set, part_set = set(ref_list), set(part_list)
    matches = ref_set == part_set
    only_in_ref = sorted(list(ref_set - part_set))
    only_in_part = sorted(list(part_set - ref_set))
    return matches, only_in_ref, only_in_part


def compare_blocks(ref_block: EnforcerBlock, part_block: EnforcerBlock) -> Tuple[bool, Optional[Dict]]:
    """Compare two blocks with the same timestamp."""
    ref_causes, ref_suppressions = parse_block_actions(ref_block)
    part_causes, part_suppressions = parse_block_actions(part_block)
    
    ref_labels = [line for line in ref_block.lines if line.startswith('[Enforcer:Label]')]
    part_labels = [line for line in part_block.lines if line.startswith('[Enforcer:Label]')]
    
    causes_match, causes_only_ref, causes_only_part = compare_lists(ref_causes, part_causes)
    suppressions_match, supp_only_ref, supp_only_part = compare_lists(ref_suppressions, part_suppressions)
    labels_match, labels_only_ref, labels_only_part = compare_lists(ref_labels, part_labels)
    
    if causes_match and suppressions_match and labels_match:
        return True, None
    
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
            "labels": {"only_in_reference": labels_only_ref, "only_in_partition": labels_only_part},
            "causes": {"only_in_reference": causes_only_ref, "only_in_partition": causes_only_part},
            "suppressions": {"only_in_reference": supp_only_ref, "only_in_partition": supp_only_part}
        }
    }
    return False, diff_dict


def compare_enforcer_outputs(reference_output: str, partition_output: str, partition_name: str = "partition") -> Dict:
    """Compare two enforcer outputs block by block using timepoint-based matching."""
    ref_blocks = parse_enforcer_output(reference_output)
    part_blocks = parse_enforcer_output(partition_output)
    return compare_blocks_json(ref_blocks, part_blocks, partition_name)


def format_block_diff(diff_entry: Dict) -> List[str]:
    """Format a single block difference for reporting."""
    ts, tp = diff_entry['timestamp'], diff_entry['timepoint']
    block_type = diff_entry['block_type']
    ref_block = diff_entry['reference_block']
    part_block = diff_entry['partition_block']
    diffs = diff_entry['differences']
    
    lines = [f"Block timepoint={tp}, @{ts} ({block_type}):"]
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
    
    for key in ['labels', 'causes', 'suppressions']:
        if diffs[key]['only_in_reference'] or diffs[key]['only_in_partition']:
            lines.append(f"  {key.capitalize()} differ:")
            if diffs[key]['only_in_reference']:
                val = len(diffs[key]['only_in_reference']) if key == 'labels' else diffs[key]['only_in_reference']
                lines.append(f"    Only in reference: {val}" + (" labels" if key == 'labels' else ""))
            if diffs[key]['only_in_partition']:
                val = len(diffs[key]['only_in_partition']) if key == 'labels' else diffs[key]['only_in_partition']
                lines.append(f"    Only in partition: {val}" + (" labels" if key == 'labels' else ""))
    
    lines.append("")
    return lines


def format_comparison_report(comparison: Dict) -> str:
    """Format comparison results as a readable report."""
    lines = ["=" * 80, f"ENFORCER OUTPUT COMPARISON: {comparison['partition_name']}", "=" * 80, ""]
    
    summary = comparison['summary']
    lines.append("SUMMARY:")
    lines.extend([
        f"  Total blocks: {summary['total_blocks']}",
        f"  Matching blocks: {summary['matching_blocks']}",
        f"  Differing blocks: {summary['differing_blocks']}",
        f"  Match percentage: {summary['match_percentage']:.2f}%",
        ""
    ])
    
    # Helper to format entry lists
    def format_entries(entries, title, limit=10):
        if not entries:
            return
        lines.append(f"{title} ({len(entries)} blocks):")
        for entry in entries[:limit]:
            lines.append(f"  timepoint={entry['timepoint']}, @{entry['timestamp']} ({entry['block_type']})")
        if len(entries) > limit:
            lines.append(f"  ... and {len(entries) - limit} more")
        lines.append("")
    
    format_entries(comparison['missing_in_partition'], "MISSING IN PARTITION")
    format_entries(comparison['extra_in_partition'], "EXTRA IN PARTITION")
    
    if comparison['differing_blocks']:
        lines.append(f"DIFFERING BLOCKS ({len(comparison['differing_blocks'])} blocks):")
        lines.append("")
        for diff_entry in comparison['differing_blocks'][:20]:
            lines.extend(format_block_diff(diff_entry))
        if len(comparison['differing_blocks']) > 20:
            lines.append(f"... and {len(comparison['differing_blocks']) - 20} more differing blocks")
            lines.append("")
    
    return '\n'.join(lines)


def save_comparison_report(comparison: Dict, output_file: str):
    """Save comparison report to file (plaintext format)."""
    with open(output_file, 'w') as f:
        f.write(format_comparison_report(comparison))


def save_comparison_json(comparison: Dict, output_file: str):
    """Save comparison results as JSON."""
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2)


def blocks_to_json_file(blocks: List[EnforcerBlock], output_file: str, timing_map: Optional[Dict[int, Dict]] = None):
    """Save parsed blocks as JSON file."""
    blocks_data = [
        block.to_dict(timing_info=timing_map.get(block.timepoint) if timing_map else None)
        for block in blocks
    ]
    
    with open(output_file, 'w') as f:
        json.dump({'total_blocks': len(blocks), 'blocks': blocks_data}, f, indent=2)


def load_blocks_from_json(json_file: str) -> List[EnforcerBlock]:
    """Load blocks from JSON file."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    return [EnforcerBlock.from_dict(block_data) for block_data in data['blocks']]


def compare_blocks_json(ref_blocks: List[EnforcerBlock], part_blocks: List[EnforcerBlock], partition_name: str = "partition") -> Dict:
    """Compare two lists of blocks using timepoint-based matching."""
    ref_dict = {block.timepoint: block for block in ref_blocks}
    part_dict = {block.timepoint: block for block in part_blocks}
    all_timepoints = sorted(set(ref_dict.keys()) | set(part_dict.keys()))
    
    matching_blocks = 0
    differing_blocks_details = []
    missing_in_partition = []
    extra_in_partition = []
    
    for tp in all_timepoints:
        ref_block, part_block = ref_dict.get(tp), part_dict.get(tp)
        
        if ref_block and part_block:
            matches, diff_dict = compare_blocks(ref_block, part_block)
            if matches:
                matching_blocks += 1
            else:
                differing_blocks_details.append({
                    "timepoint": tp,
                    "timestamp": ref_block.timestamp,
                    "block_type": ref_block.block_type,
                    **diff_dict
                })
        elif ref_block:
            missing_in_partition.append({
                "timepoint": tp,
                "timestamp": ref_block.timestamp,
                "block_type": ref_block.block_type
            })
        elif part_block:
            extra_in_partition.append({
                "timepoint": tp,
                "timestamp": part_block.timestamp,
                "block_type": part_block.block_type
            })
    
    total_blocks = len(all_timepoints)
    match_percentage = (matching_blocks / total_blocks * 100) if total_blocks > 0 else 0.0
    
    return {
        'partition_name': partition_name,
        'summary': {
            'total_blocks': total_blocks,
            'matching_blocks': matching_blocks,
            'differing_blocks': len(differing_blocks_details),
            'match_percentage': match_percentage
        },
        'missing_in_partition': missing_in_partition,
        'extra_in_partition': extra_in_partition,
        'differing_blocks': differing_blocks_details
    }
