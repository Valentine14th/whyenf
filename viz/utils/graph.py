"""
Utilities for building and manipulating the graph structure.
"""

import json
import networkx as nx
from .config import NODE_COLORS, EDGE_COLORS


def add_rule_nodes(net, rules):
    """Add rule nodes to the network."""
    for rule in rules:
        rule_id = rule['id']
        rule_type = rule.get('type', 'Unknown')
        
        # Create label with rule type
        effects_list = sorted(rule['effects'])
        rule_num = rule['id'].replace('RULE_', '')
        label = f"Rule {rule_num}"
        
        # Create hover text with details
        hover_text = (
            f"Rule {rule_num}\n"
            f"Type: {rule_type}\n"
            f"Filter ({len(rule['filter'])} predicates):\n" +
            "\n".join(f"  • {p}" for p in sorted(rule['filter'])) +
            f"\n\nEffects ({len(rule['effects'])} predicates):\n" +
            "\n".join(f"  • {p}" for p in effects_list)
        )
        
        # Color based on rule type
        color = NODE_COLORS["caubycau"] if rule_type == "CauByCau" else NODE_COLORS["caubysup"]
        
        net.add_node(
            rule_id,
            label=label,
            color=color,
            shape="box",
            size=35,
            font={"size": 14, "color": "#ffffff", "bold": True},
            shapeProperties={"borderRadius": 6},
            title=hover_text
        )

# Helper function to merge event monotonicity
def _merge_event_polarity(events_dict, pred, polarity):
    """Merge event polarity, combining different polarities into Mixed."""
    if pred not in events_dict:
        events_dict[pred] = polarity
    elif events_dict[pred] != polarity:
        # Different polarities, then mark as Mixed
        events_dict[pred] = 'Mixed'


def _expand_predicates_recursively(predicates, let_definitions_dict, events_dict=None):
    """Recursively expand LET predicates until only base predicates remain.
    
    Args:
        predicates: Set of predicate names (may include LET names)
        let_definitions_dict: Dict mapping LET names to their definitions
        events_dict: Optional dict to accumulate event polarities
    
    Returns:
        Set of fully expanded base predicates
    """
    if not let_definitions_dict:
        return predicates
    
    expanded = set()
    to_expand = set(predicates)
    visited = set()  # Track predicates we've already processed
    
    # Safety limit to prevent infinite loops
    max_iterations = 100
    iteration = 0
    
    while to_expand and iteration < max_iterations:
        iteration += 1
        current = to_expand.pop()
        
        # Skip if already processed
        if current in visited:
            continue
        visited.add(current)
        
        if current in let_definitions_dict:
            # It's a LET - add its constituents to expand queue
            let_def = let_definitions_dict[current]
            to_expand.update(let_def['predicates'])
            
            # Merge events if tracking them
            if events_dict is not None:
                for event_pred, polarity in let_def.get('events', {}).items():
                    _merge_event_polarity(events_dict, event_pred, polarity)
        else:
            # Base predicate - add to result
            expanded.add(current)
    
    if iteration >= max_iterations:
        print(f"WARNING: Maximum iteration limit reached during LET expansion!")
        print(f"  Starting predicates: {predicates}")
        print(f"  Remaining to expand: {to_expand}")
        print(f"  Already visited: {len(visited)} predicates")
        print(f"  This should never happen with the visited set - possible bug!")
    
    return expanded


def add_rule_edges(net, rules, let_definitions_dict=None):
    """Add edges between rules where one rule's effects appear in another's filter.
    
    Handles both direct predicates and LET definitions by recursively expanding LETs
    into their constituent predicates before analysis.
    
    Args:
        net: PyVis network
        rules: List of rule dictionaries
        let_definitions_dict: Dict mapping LET definition names to their data (optional)
    
    Edge color is determined by the monotonicity of shared predicates in the target rule's filter:
    - Green: All shared predicates are Monotonic
    - Orange: All shared predicates are Antimonotonic  
    - Purple: Mixed monotonicity
    """
    # Expand rules: recursively replace LET predicates with their constituents
    expanded_rules = []
    for rule in rules:
        # Start with events from original rule, then merge LET events
        filter_events = rule.get('events', {}).copy()
        
        # Expand filter predicates recursively
        expanded_filter = _expand_predicates_recursively(
            rule['filter'], 
            let_definitions_dict, 
            filter_events
        )
        
        # Expand effect predicates recursively
        expanded_effects = _expand_predicates_recursively(
            rule['effects'], 
            let_definitions_dict
        )
        
        expanded_rules.append({
            'id': rule['id'],
            'filter': expanded_filter,
            'effects': expanded_effects,
            'events': filter_events
        })
    
    # Now do simple shared predicate analysis
    edge_count = 0
    stats = {
        'monotonic': 0,
        'antimonotonic': 0,
        'mixed': 0
    }
    
    for rule_from in expanded_rules:
        for rule_to in expanded_rules:
            if rule_from['id'] == rule_to['id']:
                continue
            
            # Check if any of rule_from's effects appear in rule_to's filter
            common_predicates = rule_from['effects'] & rule_to['filter']
            
            if common_predicates:
                # Determine monotonicity
                events = rule_to['events']
                monotonicities = set()
                monotonicity_details = []
                
                for pred in common_predicates:
                    polarity = events.get(pred, 'Mixed')
                    monotonicities.add(polarity)
                    monotonicity_details.append(f"{pred} ({polarity})")
                
                # Determine edge color based on monotonicity
                if monotonicities == {'Monotonic'}:
                    edge_color = "#27ae60"
                    monotonicity_type = "monotonic"
                    stats['monotonic'] += 1
                elif monotonicities == {'Antimonotonic'}:
                    edge_color = "#e67e22"
                    monotonicity_type = "antimonotonic"
                    stats['antimonotonic'] += 1
                else:
                    edge_color = "#9b59b6"
                    monotonicity_type = "mixed"
                    stats['mixed'] += 1
                
                # Create edge title
                rule_from_num = rule_from['id'].replace('RULE_', '')
                rule_to_num = rule_to['id'].replace('RULE_', '')
                
                pred_str = ", ".join(sorted(common_predicates))
                title = (
                    f"Rule {rule_from_num} → Rule {rule_to_num}\n"
                    f"Shared predicates: {pred_str}\n"
                    f"Monotonicity: {monotonicity_type.capitalize()}\n" +
                    "\n".join(f"  • {detail}" for detail in sorted(monotonicity_details))
                )
                
                # Create edge
                net.add_edge(
                    rule_from['id'],
                    rule_to['id'],
                    color={"color": edge_color, "highlight": "#e74c3c", "opacity": 0.7},
                    width=2,
                    title=title,
                    label=str(len(common_predicates)),
                    monotonicity_type=monotonicity_type
                )
                edge_count += 1
    
    # Print statistics
    _print_edge_statistics(edge_count, stats)
    shared_predicate_count = _compute_shared_predicates(net.edges)
    _print_shared_predicates(shared_predicate_count)
    
    return edge_count


def filter_polarity_edges(net, rules):
    """Remove polarity edges from the graph.
    
    Removes edges where:
    - Source node is CauBySup AND edge is monotonic, OR
    - Source node is CauByCau AND edge is antimonotonic
    
    These are edges where a rule causally depends on predicates with the opposite
    monotonicity type (polarity causality).
    
    Args:
        net: PyVis network with edges to filter
        rules: List of rule dictionaries with 'id' and 'type' fields
    
    Returns:
        Number of edges removed
    """
    # Build mapping of rule ID to rule type
    rule_type_map = {rule['id']: rule.get('type', 'Unknown') for rule in rules}
    
    # Find edges to remove
    edges_to_remove = []
    for i, edge in enumerate(net.edges):
        source_id = edge['from']
        monotonicity_type = edge.get('monotonicity_type', '')
        
        # Get source node type
        source_type = rule_type_map.get(source_id)
        
        # Check if edge should be removed
        if (source_type == 'CauBySup' and monotonicity_type == 'monotonic') or \
           (source_type == 'CauByCau' and monotonicity_type == 'antimonotonic'):
            edges_to_remove.append(i)
    
    # Remove edges in reverse order to maintain indices
    removed_count = len(edges_to_remove)
    for idx in reversed(edges_to_remove):
        net.edges.pop(idx)
    
    if removed_count > 0:
        print(f"\nFiltered {removed_count} polarity edges:")
        print(f"  - CauByCau with antimonotonic edges")
        print(f"  - CauBySup with monotonic edges")
        
        # Count remaining edges by monotonicity
        remaining_stats = {
            'monotonic': 0,
            'antimonotonic': 0,
            'mixed': 0
        }
        for edge in net.edges:
            monotonicity_type = edge.get('monotonicity_type', '')
            if monotonicity_type in remaining_stats:
                remaining_stats[monotonicity_type] += 1
        
        remaining_total = sum(remaining_stats.values())
        print(f"\nRemaining edges after filtering: {remaining_total}")
        if remaining_total > 0:
            print(f"  By monotonicity:")
            print(f"    - Monotonic: {remaining_stats['monotonic']} ({100*remaining_stats['monotonic']/remaining_total:.1f}%)")
            print(f"    - Antimonotonic: {remaining_stats['antimonotonic']} ({100*remaining_stats['antimonotonic']/remaining_total:.1f}%)")
            print(f"    - Mixed: {remaining_stats['mixed']} ({100*remaining_stats['mixed']/remaining_total:.1f}%)")
        
        # Compute and print shared predicates after filtering
        shared_after = _compute_shared_predicates(net.edges)
        _print_shared_predicates(shared_after, " (after polarity filtering)")
    
    return removed_count


def get_node_id(pred_name, let_definition_names):
    """Return the correct node ID (LET node or predicate node)."""
    return f"LET_{pred_name}" if pred_name in let_definition_names else pred_name


def extract_node_name(node_id):
    """Extract node name without LET_ prefix."""
    return node_id[4:] if node_id.startswith('LET_') else node_id


def calculate_edge_properties(count, base_width=1.5, base_opacity=0.5, 
                             width_increment=0.5, opacity_increment=0.1, 
                             max_width=6, max_opacity=0.95):
    """Calculate edge width and opacity based on count."""
    width = min(base_width + (count - 1) * width_increment, max_width)
    opacity = min(base_opacity + (count - 1) * opacity_increment, max_opacity)
    return width, opacity


def get_causality_color(rule_types):
    """Determine edge color based on causality rule types."""
    if rule_types == {"CauByCau"}:
        return EDGE_COLORS["caubycau"]
    elif rule_types == {"CauBySup"}:
        return EDGE_COLORS["caubysup"]
    else:
        return EDGE_COLORS["mixed"]


def add_predicate_nodes(net, predicates, let_predicates, implication_predicates, 
                       causality_predicates, let_definition_names):
    """Add all predicate nodes to the network."""
    def build_predicate_title(pred):
        title_parts = [f"Predicate: {pred}"]
        locations = []
        if pred in let_predicates:
            locations.append("LET definitions")
        if pred in implication_predicates:
            locations.append("implications")
        if pred in causality_predicates:
            locations.append("causality rules")
        if locations:
            title_parts.append(f"(Used in {' and '.join(locations)})")
        return "\n".join(title_parts)
    
    for pred in predicates:
        net.add_node(
            pred,
            label=pred,
            color=NODE_COLORS["predicate"],
            shape="dot",
            size=25,
            font={"size": 14, "color": "#2c3e50"},
            title=build_predicate_title(pred)
        )


def add_let_definition_nodes(net, definitions):
    """Add all LET definition nodes to the network."""
    for defn in definitions:
        let_id = f"LET_{defn['name']}"
        predicates_list = sorted(defn['predicates'])
        hover_text = (
            f"LET definition: {defn['name']}\nType: {defn['type']}\n"
            f"Uses {len(defn['predicates'])} predicates:\n" +
            "\n".join(f"  • {p}" for p in predicates_list)
        )
        net.add_node(
            let_id,
            label=defn['name'],
            color=NODE_COLORS["let"],
            shape="box",
            size=30,
            font={"size": 15, "color": "#ffffff", "bold": True},
            shapeProperties={"borderRadius": 6},
            title=hover_text
        )


def add_let_definition_edges(net, definitions, let_definition_names):
    """Add edges from LET definitions to their predicates."""
    edge_count = 0
    for defn in definitions:
        let_id = f"LET_{defn['name']}"
        for pred in defn["predicates"]:
            net.add_edge(
                get_node_id(pred, let_definition_names),
                let_id,
                color={"color": EDGE_COLORS["let"], "highlight": "#e67e22", "opacity": 0.6},
                width=2,
                title=f"{pred} used by {defn['name']}"
            )
            edge_count += 1
    return edge_count


def add_causality_edges(net, rules, let_definition_names):
    """Add edges from causality rules (CauByCau and CauBySup)."""
    # Aggregate causality edges
    causality_edges = {}  # (source, target) -> {count, types}
    for rule in rules:
        for filter_pred in rule["filter"]:
            for effect_pred in rule["effects"]:
                edge_key = (
                    get_node_id(filter_pred, let_definition_names),
                    get_node_id(effect_pred, let_definition_names)
                )
                if edge_key not in causality_edges:
                    causality_edges[edge_key] = {"count": 0, "types": set()}
                causality_edges[edge_key]["count"] += 1
                causality_edges[edge_key]["types"].add(rule["type"])
    
    # Create edges with aggregated properties
    edge_count = 0
    for (filter_node, effect_node), data in causality_edges.items():
        count = data["count"]
        width, opacity = calculate_edge_properties(count, base_width=2, base_opacity=0.6)
        rule_types_str = ", ".join(sorted(data["types"]))
        plural = "rules" if count > 1 else "rule"
        
        net.add_edge(
            filter_node,
            effect_node,
            color={
                "color": get_causality_color(data["types"]),
                "highlight": "#f39c12",
                "opacity": opacity
            },
            width=width,
            title=f"Causality: {filter_node} → {effect_node}\n({count} {plural}: {rule_types_str})"
        )
        edge_count += 1
    
    return edge_count


def add_implication_edges(net, implications, let_definition_names):
    """Add edges from implications for legacy non-normalized graph."""
    # Aggregate implication edges
    implication_edges = {}  # (source, target) -> count
    for imp in implications:
        for left_pred in imp["left"]:
            for right_pred in imp["right"]:
                edge_key = (
                    get_node_id(left_pred, let_definition_names),
                    get_node_id(right_pred, let_definition_names)
                )
                implication_edges[edge_key] = implication_edges.get(edge_key, 0) + 1
    
    # Create implication edges with aggregated properties
    edge_count = 0
    for (left_node, right_node), count in implication_edges.items():
        width, opacity = calculate_edge_properties(count, base_width=1.5, base_opacity=0.5, max_width=5)
        plural = "implications" if count > 1 else "implication"
        
        net.add_edge(
            left_node,
            right_node,
            color={"color": EDGE_COLORS["implication"], "highlight": "#e74c3c", "opacity": opacity},
            width=width,
            dashes=[5, 5],
            title=f"Implication: {left_node} → {right_node}\n({count} {plural})"
        )
        edge_count += 1
    
    return edge_count


def find_sccs(net):
    """Find Strongly Connected Components in the graph."""
    nx_graph = nx.DiGraph()
    for node in net.nodes:
        nx_graph.add_node(node['id'])
    for edge in net.edges:
        nx_graph.add_edge(edge['from'], edge['to'])
    
    sccs = [list(scc) for scc in nx.strongly_connected_components(nx_graph) if len(scc) > 1]
    scc_map = {}
    for i, scc in enumerate(sccs):
        for node_id in scc:
            scc_map[node_id] = i
            
    print(f"Found {len(sccs)} SCCs with more than one node.")
    return sccs, scc_map


def _build_graph_and_compute_sccs(net):
    """Build networkx graph and compute all SCCs.
    
    Returns:
        - nx_graph: NetworkX DiGraph
        - sccs_all: List of all SCCs (list of node lists)
        - scc_map_all: Dict mapping node_id to SCC index
        - condensed: Condensed graph (DAG of SCCs)
    """
    # Build networkx graph
    nx_graph = nx.DiGraph()
    for node in net.nodes:
        nx_graph.add_node(node['id'])
    for edge in net.edges:
        nx_graph.add_edge(edge['from'], edge['to'])
    
    # Find all SCCs
    sccs_all = list(nx.strongly_connected_components(nx_graph))
    sccs_all = [list(scc) for scc in sccs_all]
    scc_map_all = {}
    for i, scc in enumerate(sccs_all):
        for node_id in scc:
            scc_map_all[node_id] = i
    
    # Create condensed graph (DAG of SCCs)
    condensed = nx.condensation(nx_graph)
    
    return nx_graph, sccs_all, scc_map_all, condensed


def _merge_partitions(partitions, partition_labels, sccs_all):
    """Merge partitions with identical node sets.
    
    Excludes anchor nodes before comparing (merge if same descendants).
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
    
    Returns:
        - merged_partitions: Dict of merged partitions
        - merged_labels: Dict of merged labels
        - node_set_to_anchors: Dict mapping node sets to anchor indices (for statistics)
    """
    # Group partitions by their node sets
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
    for frozen_nodes, anchor_indices in node_set_to_anchors.items():
        # Skip partitions with 0 non-leaf nodes
        if len(frozen_nodes) == 0:
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
    
    return merged_partitions, merged_labels, node_set_to_anchors


def _print_partition_statistics(sccs_all, anchor_sccs, partitions, merged_partitions, partition_type):
    """Print partition computation statistics.
    
    Args:
        sccs_all: List of all SCCs
        anchor_sccs: List of anchor SCC indices (sources or leaves)
        partitions: Dict of initial partitions before merging
        merged_partitions: Dict of partitions after merging
        partition_type: "source" or "leaf" for display purposes
    """
    print(f"\nPartition Statistics ({partition_type}-based):")
    print(f"Found {len(sccs_all)} SCCs (including trivial ones)")
    print(f"Found {len(anchor_sccs)} {partition_type} SCCs in condensed graph")
    print(f"Computed {len(partitions)} initial {partition_type}-based partitions")
    print(f"Merged into {len(merged_partitions)} unique partitions\n")


def _print_common_nodes(partitions, partition_labels):
    """Print nodes that are common to all partitions.
    
    Args:
        partitions: Dict mapping partition index to set of node IDs
        partition_labels: Dict mapping partition index to label string
    """
    if not partitions:
        print("No partitions to analyze for common nodes.")
        return
    
    if len(partitions) == 1:
        print("Only one partition exists - all nodes are 'common' to that partition.")
        return
    
    # Compute intersection of all partitions
    partition_list = list(partitions.values())
    common_nodes = set(partition_list[0])
    
    for partition_nodes in partition_list[1:]:
        common_nodes &= partition_nodes
    
    # Print results
    print(f"Nodes common to all {len(partitions)} partitions: {len(common_nodes)}")
    
    if common_nodes:
        # Sort by extracting rule number for nicer display
        def sort_key(node_id):
            if node_id.startswith('RULE_'):
                try:
                    return (0, int(node_id.replace('RULE_', '')))
                except:
                    return (0, 0)
            return (1, node_id)
        
        sorted_nodes = sorted(common_nodes, key=sort_key)
        
        # Print in columns for better readability
        print("  Common nodes:")
        for i in range(0, len(sorted_nodes), 5):
            batch = sorted_nodes[i:i+5]
            print("    " + ", ".join(batch))
        print()
    else:
        print("  No nodes are common to all partitions.\n")


def compute_backward_partitions(net):
    """
    Compute backward-reachable partitions from leaves (NOT successor-closed).
    
    Each partition includes only nodes that can reach a leaf node (node with no outgoing 
    edges). 
    
    Returns:
        - sccs_all: List of all SCCs (list of node lists)
        - scc_map_all: Dict mapping node_id to SCC index
        - partitions: Dict mapping leaf SCC index to set of backward-reachable node IDs
        - partition_labels: Dict mapping leaf SCC index to leaf node name
        - condensed_graph: The condensed NetworkX graph
        - stats: Dict with partition statistics
    """
    nx_graph, sccs_all, scc_map_all, condensed = _build_graph_and_compute_sccs(net)
    
    # Find leaf nodes in condensed graph (no outgoing edges)
    leaf_sccs = [node for node in condensed.nodes() if condensed.out_degree(node) == 0]
    
    # For each leaf SCC, compute backward-reachable set 
    partitions = {}
    partition_labels = {}
    for leaf_scc_idx in leaf_sccs:
        # Get all SCCs that can reach this leaf SCC (predecessors/ancestors in DAG)
        backward_reachable_sccs = nx.ancestors(condensed, leaf_scc_idx)
        backward_reachable_sccs.add(leaf_scc_idx)  # Include the leaf itself
        
        # Expand to original nodes 
        partition_nodes = set()
        for scc_idx in backward_reachable_sccs:
            partition_nodes.update(sccs_all[scc_idx])
        
        partitions[leaf_scc_idx] = partition_nodes
        partition_labels[leaf_scc_idx] = extract_node_name(sorted(sccs_all[leaf_scc_idx])[0])
    
    # Merge partitions with identical node sets
    merged_partitions, merged_labels, node_set_to_anchors = _merge_partitions(
        partitions, partition_labels, sccs_all
    )
    
    _print_partition_statistics(sccs_all, leaf_sccs, partitions, merged_partitions, "backward")
    
    # Compute and print common nodes across all partitions
    _print_common_nodes(merged_partitions, merged_labels)
    
    stats = {
        'initial_count': len(partitions),
        'merged_count': len(merged_partitions),
        'strategy': 'Merge if same nodes (excluding leaves)'
    }
    
    return sccs_all, scc_map_all, merged_partitions, merged_labels, condensed, stats


def find_source_and_leaf_nodes(net):
    """Identify and color leaf and source nodes based on graph structure."""
    all_edges = net.edges
    all_node_ids = {node['id'] for node in net.nodes}
    nodes_with_outgoing = {edge['from'] for edge in all_edges}
    nodes_with_incoming = {edge['to'] for edge in all_edges}
    
    leaf_nodes = all_node_ids - nodes_with_outgoing
    source_nodes = all_node_ids - nodes_with_incoming
    
    # Update node colors for leaf and source nodes
    for node in net.nodes:
        if node['id'].startswith('RULE_'):
            # Keep the original rule type color but indicate special status in title
            if node['id'] in leaf_nodes:
                node['title'] = node.get('title', '') + '\n[LEAF NODE - no outgoing edges]'
            elif node['id'] in source_nodes:
                node['title'] = node.get('title', '') + '\n[SOURCE NODE - no incoming edges]'
        else:
            # Legacy support for LET/predicate nodes if they exist
            is_let_node = node['id'].startswith('LET_')
            if node['id'] in leaf_nodes:
                node['color'] = NODE_COLORS["leaf_let" if is_let_node else "leaf_pred"]
            elif node['id'] in source_nodes:
                node['color'] = NODE_COLORS["source_let" if is_let_node else "source_pred"]
    
    return leaf_nodes, source_nodes


def print_graph_statistics(definitions, predicate_only_names, edge_count, 
                          implications, implication_edge_count, rules=None, 
                          causality_edge_count=0, mode="original"):
    """Print comprehensive statistics about the graph."""
    total_nodes = len(predicate_only_names) + len(definitions)
    print(f"\nGraph Statistics:")
    print(f"  Nodes:")
    print(f"    - LET definitions: {len(definitions)}")
    print(f"    - Unique predicates: {len(predicate_only_names)}")
    print(f"    - Total nodes: {total_nodes}")
    print(f"  Edges:")
    if mode == "original" and definitions:
        print(f"    - LET definition edges: {edge_count}")
    if mode == "normal" and rules:
        print(f"    - Causality rules: {len(rules)}")
        print(f"    - Causality edges: {causality_edge_count}")
    print(f"    - Implications: {len(implications)}")
    print(f"    - Implication edges: {implication_edge_count}")
    if mode == "original" and definitions and edge_count > 0:
        print(f"  Average predicates per LET definition: {edge_count / len(definitions):.2f}")
    
    # Print top used predicates
    if definitions:
        predicate_usage = {}
        for defn in definitions:
            for pred in defn["predicates"]:
                predicate_usage[pred] = predicate_usage.get(pred, 0) + 1
        
        if predicate_usage:
            most_used = sorted(predicate_usage.items(), key=lambda x: x[1], reverse=True)[:10]
            print(f"\n  Top 10 most used predicates:")
            for pred, count in most_used:
                print(f"    - {pred}: used in {count} definition{'s' if count > 1 else ''}")


def _compute_shared_predicates(edges):
    """Compute how often each predicate is shared across edges.
    
    Args:
        edges: List of edge dictionaries with 'title' field containing predicate info
    
    Returns:
        Dictionary mapping predicate name to count of edges it appears in
    """
    shared_predicate_count = {}
    
    for edge in edges:
        title = edge.get('title', '')
        # Extract predicates from title line "Shared predicates: pred1, pred2, ..."
        if 'Shared predicates:' in title:
            lines = title.split('\n')
            for line in lines:
                if line.startswith('Shared predicates:'):
                    pred_str = line.replace('Shared predicates:', '').strip()
                    predicates = [p.strip() for p in pred_str.split(',')]
                    for pred in predicates:
                        if pred:
                            shared_predicate_count[pred] = shared_predicate_count.get(pred, 0) + 1
    
    return shared_predicate_count


def _print_shared_predicates(shared_predicate_count, label=""):
    """Print top 10 most shared predicates.
    
    Args:
        shared_predicate_count: Dict mapping predicate name to count
        label: Optional label to distinguish different printouts
    """
    if shared_predicate_count:
        top_shared = sorted(shared_predicate_count.items(), key=lambda x: x[1], reverse=True)[:10]
        print(f"\n  Top 10 most shared predicates{label}:")
        for pred, count in top_shared:
            print(f"    - {pred}: shared in {count} edge{'s' if count > 1 else ''}")


def _print_edge_statistics(edge_count, stats):
    """Print edge statistics including monotonicity breakdown.
    
    Args:
        edge_count: Total number of edges
        stats: Dictionary with keys 'monotonic', 'antimonotonic', 'mixed'
    """
    print(f"\nEdge Statistics:")
    print(f"  Total edges: {edge_count}")
    
    if edge_count > 0:
        print(f"  By monotonicity:")
        print(f"    - Monotonic: {stats['monotonic']} ({100*stats['monotonic']/edge_count:.1f}%)")
        print(f"    - Antimonotonic: {stats['antimonotonic']} ({100*stats['antimonotonic']/edge_count:.1f}%)")
        print(f"    - Mixed: {stats['mixed']} ({100*stats['mixed']/edge_count:.1f}%)")
    else:
        print(f"  By monotonicity:")
        print(f"    - Monotonic: 0")
        print(f"    - Antimonotonic: 0")
        print(f"    - Mixed: 0")
