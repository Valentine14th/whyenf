"""
Partition merging strategies for graph analysis.

This module provides different strategies for merging partitions.
"""

import math


def _split_into_balanced_groups(items, max_size):
    """Split items into balanced groups not exceeding max_size.
    
    Args:
        items: List of items to split
        max_size: Maximum size per group
    
    Returns:
        List of groups (each group is a list of items)
    """
    if not max_size or len(items) <= max_size:
        return [items]
    
    num_groups = math.ceil(len(items) / max_size)
    group_size = math.ceil(len(items) / num_groups)
    
    groups = []
    for group_idx in range(num_groups):
        start_idx = group_idx * group_size
        end_idx = min(start_idx + group_size, len(items))
        group = items[start_idx:end_idx]
        if group:
            groups.append(group)
    
    return groups


def _create_partition_label(anchor_names, num_nodes, is_leaf_only=False, group_idx=None, total_groups=None):
    """Create a label for a merged partition.
    
    Args:
        anchor_names: Sorted list of anchor names
        num_nodes: Total number of nodes in partition
        is_leaf_only: Whether this partition contains only leaf nodes
        group_idx: Optional group index (0-based)
        total_groups: Optional total number of groups
    
    Returns:
        Formatted label string
    """
    # Create base label from anchor names
    if len(anchor_names) == 1:
        label_base = anchor_names[0]
    else:
        label_base = f"{', '.join(anchor_names[:-1])} & {anchor_names[-1]}"
    
    # Create suffix
    suffix = f"leaf{'ves' if len(anchor_names) > 1 else ''}"
    
    # Create group indicator if needed
    group_indicator = ""
    if group_idx is not None and total_groups is not None and total_groups > 1:
        group_indicator = f" [group {group_idx + 1}/{total_groups}]"
    
    # Assemble final label
    if is_leaf_only:
        return f"{label_base} ({len(anchor_names)} {suffix} only){group_indicator}"
    else:
        non_leaf_count = num_nodes - len(anchor_names)
        return f"{label_base} ({non_leaf_count} nodes, {len(anchor_names)} {suffix}){group_indicator}"


def _process_partition_group(group_anchors, frozen_nodes, sccs_all, partition_labels, 
                             is_leaf_only=False, group_idx=None, total_groups=None):
    """Process a group of anchors into a merged partition.
    
    Args:
        group_anchors: List of anchor SCC indices to merge
        frozen_nodes: Frozenset of descendant nodes (excluding anchors)
        sccs_all: List of all SCCs
        partition_labels: Dict mapping anchor SCC index to label
        is_leaf_only: Whether this is a leaf-only partition
        group_idx: Optional group index (0-based)
        total_groups: Optional total number of groups
    
    Returns:
        Tuple of (key_idx, merged_nodes, label)
    """
    key_idx = group_anchors[0]
    
    # Create merged node set from anchors and descendants
    all_nodes = set(frozen_nodes)
    for idx in group_anchors:
        all_nodes.update(sccs_all[idx])
    
    anchor_names = sorted([partition_labels[idx] for idx in group_anchors])
    label = _create_partition_label(
        anchor_names, len(all_nodes), is_leaf_only, group_idx, total_groups
    )
    return key_idx, all_nodes, label


def merge_by_descendants(partitions, partition_labels, sccs_all, max_merge_size=None):
    """Merge partitions with identical descendant nodes (excluding anchor nodes).
    
    This strategy groups partitions by comparing only their non-anchor nodes.
    Partitions with the same descendant set are merged together.
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
        max_merge_size: Maximum number of partitions to merge together (None for unlimited)
    
    Returns:
        - merged_partitions: Dict of merged partitions
        - merged_labels: Dict of merged labels
    """
    # Group partitions by their node sets (excluding anchors)
    node_set_to_anchors = {}
    for anchor_idx, nodes in partitions.items():
        # Exclude anchor nodes from comparison
        anchor_scc_nodes = set(sccs_all[anchor_idx])
        comparison_nodes = nodes - anchor_scc_nodes
        
        frozen_nodes = frozenset(comparison_nodes)
        
        if frozen_nodes not in node_set_to_anchors:
            node_set_to_anchors[frozen_nodes] = []
        node_set_to_anchors[frozen_nodes].append(anchor_idx)
    
    # Create merged partitions and labels
    merged_partitions = {}
    merged_labels = {}
    leaf_only_anchors = []  # Collect all partitions with only anchor nodes (no descendants)
    
    for frozen_nodes, anchor_indices in node_set_to_anchors.items():
        # Bundle all partitions with 0 non-leaf nodes into one
        if len(frozen_nodes) == 0:
            leaf_only_anchors.extend(anchor_indices)
            continue
        
        # Split into balanced groups if needed
        groups = _split_into_balanced_groups(anchor_indices, max_merge_size)
        
        # Process each group
        for group_idx, group_anchors in enumerate(groups):
            key_idx, all_nodes, label = _process_partition_group(
                group_anchors, frozen_nodes, sccs_all, partition_labels,
                is_leaf_only=False, group_idx=group_idx, total_groups=len(groups)
            )
            merged_partitions[key_idx] = all_nodes
            merged_labels[key_idx] = label
    
    # Bundle all leaf-only partitions together if there are any
    if leaf_only_anchors:
        # Split into balanced groups if needed
        groups = _split_into_balanced_groups(leaf_only_anchors, max_merge_size)
        
        # Process each group
        for group_idx, group_anchors in enumerate(groups):
            key_idx, all_nodes, label = _process_partition_group(
                group_anchors, frozenset(), sccs_all, partition_labels,
                is_leaf_only=True, group_idx=group_idx, total_groups=len(groups)
            )
            merged_partitions[key_idx] = all_nodes
            merged_labels[key_idx] = label
    
    return merged_partitions, merged_labels


def no_merge(partitions, partition_labels, sccs_all, max_merge_size=None):
    """No merging - keep all partitions separate.
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
        max_merge_size: Maximum number of partitions to merge together (unused in this strategy)
    
    Returns:
        - partitions: Dict of partitions (unchanged)
        - partition_labels: Dict of labels (unchanged)
    """
    return partitions, partition_labels


# Registry of available merging strategies
MERGE_STRATEGIES = {
    'by_descendants': {
        'function': merge_by_descendants,
        'display_name': 'Merge by descendants (excluding anchors)'
    },
    'no_merge': {
        'function': no_merge,
        'display_name': 'No merging'
    }
}


def apply_merge_strategy(partitions, partition_labels, sccs_all, strategy='by_descendants', max_merge_size=None):
    """Apply the specified merge strategy.
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
        strategy: Name of the strategy to use ('by_descendants' or 'no_merge')
        max_merge_size: Maximum number of partitions to merge together (None for unlimited)
    
    Returns:
        - merged_partitions: Dict of merged partitions
        - merged_labels: Dict of merged labels
        - strategy_name: Human-readable name of the strategy used
    
    Raises:
        ValueError: If the specified strategy is not found
    """
    if strategy not in MERGE_STRATEGIES:
        available = ', '.join(MERGE_STRATEGIES.keys())
        raise ValueError(f"Unknown merge strategy '{strategy}'. Available: {available}")
    
    strategy_info = MERGE_STRATEGIES[strategy]
    merged_partitions, merged_labels = strategy_info['function'](partitions, partition_labels, sccs_all, max_merge_size)
    
    return merged_partitions, merged_labels, strategy_info['display_name']
