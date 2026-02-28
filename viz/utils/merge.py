"""
Partition merging strategies for graph analysis.

This module provides different strategies for merging partitions.
"""


def merge_by_descendants(partitions, partition_labels, sccs_all):
    """Merge partitions with identical descendant nodes (excluding anchor nodes).
    
    This strategy groups partitions by comparing only their non-anchor nodes.
    Partitions with the same descendant set are merged together.
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
    
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
            
        # Use the first anchor index as the key for the merged partition
        key_idx = anchor_indices[0]
        # Include all anchor nodes from all merged partitions
        all_nodes = set(frozen_nodes)
        for idx in anchor_indices:
            all_nodes.update(sccs_all[idx])
        merged_partitions[key_idx] = all_nodes
        
        # Create label combining all anchor names with node count
        anchor_names = sorted([partition_labels[idx] for idx in anchor_indices])
        if len(anchor_names) == 1:
            label_base = anchor_names[0]
        else:
            label_base = f"{', '.join(anchor_names[:-1])} & {anchor_names[-1]}"
        
        # Generate label with leaf suffix
        suffix = f"leaf{'ves' if len(anchor_names) > 1 else ''}"
        merged_labels[key_idx] = f"{label_base} ({len(all_nodes) - len(anchor_names)} nodes, {len(anchor_names)} {suffix})"
    
    # Bundle all leaf-only partitions together if there are any
    if leaf_only_anchors:
        key_idx = leaf_only_anchors[0]
        all_nodes = set()
        for idx in leaf_only_anchors:
            all_nodes.update(sccs_all[idx])
        merged_partitions[key_idx] = all_nodes
        
        # Create label for bundled leaf-only partition
        anchor_names = sorted([partition_labels[idx] for idx in leaf_only_anchors])
        if len(anchor_names) == 1:
            label_base = anchor_names[0]
        else:
            label_base = f"{', '.join(anchor_names[:-1])} & {anchor_names[-1]}"
        
        suffix = f"leaf{'ves' if len(anchor_names) > 1 else ''}"
        merged_labels[key_idx] = f"{label_base} ({len(anchor_names)} {suffix} only)"
    
    return merged_partitions, merged_labels


def no_merge(partitions, partition_labels, sccs_all):
    """No merging - keep all partitions separate.
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
    
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


def apply_merge_strategy(partitions, partition_labels, sccs_all, strategy='by_descendants'):
    """Apply the specified merge strategy.
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
        strategy: Name of the strategy to use ('by_descendants' or 'no_merge')
    
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
    merged_partitions, merged_labels = strategy_info['function'](partitions, partition_labels, sccs_all)
    
    return merged_partitions, merged_labels, strategy_info['display_name']
