"""
Utilities for building and manipulating the graph structure.
"""

import json
import networkx as nx
from .config import NODE_COLORS, EDGE_COLORS


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
    """Add edges from implications."""
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


def _merge_partitions(partitions, partition_labels, sccs_all, anchor_type="source"):
    """Merge partitions with identical node sets.
    
    For source partitions: Excludes anchor nodes before comparing (merge if same descendants)
    For leaf partitions: Includes anchor nodes in comparison (merge only if fully identical)
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
        anchor_type: Either "source" or "leaf" for label generation
    
    Returns:
        - merged_partitions: Dict of merged partitions
        - merged_labels: Dict of merged labels
        - node_set_to_anchors: Dict mapping node sets to anchor indices (for statistics)
    """
    # Group partitions by their node sets
    node_set_to_anchors = {}
    for anchor_idx, nodes in partitions.items():
        # For source partitions, exclude anchor nodes from comparison
        # For leaf partitions, include all nodes in comparison
        if anchor_type == "source":
            anchor_scc_nodes = set(sccs_all[anchor_idx])
            comparison_nodes = nodes - anchor_scc_nodes
        else:  # leaf partitions
            comparison_nodes = nodes
        
        frozen_nodes = frozenset(comparison_nodes)
        
        if frozen_nodes not in node_set_to_anchors:
            node_set_to_anchors[frozen_nodes] = []
        node_set_to_anchors[frozen_nodes].append(anchor_idx)
    
    # Create merged partitions and labels
    merged_partitions = {}
    merged_labels = {}
    for frozen_nodes, anchor_indices in node_set_to_anchors.items():
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
        
        # Generate appropriate suffix based on anchor type
        if anchor_type == "leaf":
            suffix = f"leaf{'ves' if len(anchor_names) > 1 else ''}"
        else:
            suffix = f"source{'s' if len(anchor_names) > 1 else ''}"
        
        merged_labels[key_idx] = f"{label_base} ({len(all_nodes) - len(anchor_names)} nodes, {len(anchor_names)} {suffix})"
    
    return merged_partitions, merged_labels, node_set_to_anchors


def compute_source_partitions(net):
    """
    Compute source-based partitions (forward-reachable, successor-closed subgraphs).
    
    Each partition corresponds to all nodes reachable from a source node (node with no 
    incoming edges) in the condensed graph. Partitions are successor-closed.
    
    Returns:
        - sccs_all: List of all SCCs (list of node lists)
        - scc_map_all: Dict mapping node_id to SCC index
        - partitions: Dict mapping source SCC index to set of all reachable node IDs
        - partition_labels: Dict mapping source SCC index to source node name
        - condensed_graph: The condensed NetworkX graph
        - stats: Dict with partition statistics
    """
    nx_graph, sccs_all, scc_map_all, condensed = _build_graph_and_compute_sccs(net)
    
    # Find source nodes in condensed graph (no incoming edges)
    source_sccs = [node for node in condensed.nodes() if condensed.in_degree(node) == 0]
    
    # For each source SCC, compute forward-reachable set (successor-closed)
    partitions = {}
    partition_labels = {}
    for source_scc_idx in source_sccs:
        # Get all SCCs reachable from this source SCC (descendants in DAG)
        reachable_sccs = nx.descendants(condensed, source_scc_idx)
        reachable_sccs.add(source_scc_idx)  # Include the source itself
        
        # Expand to original nodes
        partition_nodes = set()
        for scc_idx in reachable_sccs:
            partition_nodes.update(sccs_all[scc_idx])
        
        partitions[source_scc_idx] = partition_nodes
        partition_labels[source_scc_idx] = extract_node_name(sorted(sccs_all[source_scc_idx])[0])
    
    # Merge partitions with identical node sets
    merged_partitions, merged_labels, node_set_to_anchors = _merge_partitions(
        partitions, partition_labels, sccs_all, anchor_type="source"
    )
    
    
    print(f"Found {len(sccs_all)} SCCs (including trivial ones)")
    print(f"Found {len(source_sccs)} source SCCs in condensed graph")
    print(f"Computed {len(partitions)} initial source-based partitions")
    print(f"Merged into {len(merged_partitions)} unique partitions")
    
    # Print partition statistics
    for partition_idx, nodes in merged_partitions.items():
        source_scc_nodes = set()
        for frozen_nodes, source_indices in node_set_to_anchors.items():
            if source_indices[0] == partition_idx:
                for idx in source_indices:
                    source_scc_nodes.update(sccs_all[idx])
                break
        nodes_without_sources = nodes - source_scc_nodes
        print(f"  Partition {merged_labels[partition_idx]}: {len(nodes_without_sources)} nodes (+ {len(source_scc_nodes)} source)")
    
    stats = {
        'initial_count': len(partitions),
        'merged_count': len(merged_partitions),
        'strategy': 'Merge if same descendants (excluding sources)'
    }
    
    return sccs_all, scc_map_all, merged_partitions, merged_labels, condensed, stats


def compute_leaf_partitions(net):
    """
    Compute leaf-based partitions (backward-reachable, successor-closed subgraphs).
    
    Each partition includes all nodes that can reach a leaf node (node with no outgoing 
    edges), extended to be successor-closed.
    
    Returns:
        - sccs_all: List of all SCCs (list of node lists)
        - scc_map_all: Dict mapping node_id to SCC index
        - partitions: Dict mapping leaf SCC index to set of all reachable node IDs
        - partition_labels: Dict mapping leaf SCC index to leaf node name
        - condensed_graph: The condensed NetworkX graph
        - stats: Dict with partition statistics
    """
    nx_graph, sccs_all, scc_map_all, condensed = _build_graph_and_compute_sccs(net)
    
    # Find leaf nodes in condensed graph (no outgoing edges)
    leaf_sccs = [node for node in condensed.nodes() if condensed.out_degree(node) == 0]
    
    # For each leaf SCC, compute backward-reachable set and make it successor-closed
    partitions = {}
    partition_labels = {}
    for leaf_scc_idx in leaf_sccs:
        # Get all SCCs that can reach this leaf SCC (predecessors/ancestors in DAG)
        backward_reachable_sccs = nx.ancestors(condensed, leaf_scc_idx)
        backward_reachable_sccs.add(leaf_scc_idx)  # Include the leaf itself
        
        # Make the set successor-closed by including all descendants of backward-reachable nodes
        successor_closed_sccs = set(backward_reachable_sccs)
        for scc_idx in backward_reachable_sccs:
            descendants = nx.descendants(condensed, scc_idx)
            successor_closed_sccs.update(descendants)
        
        # Expand to original nodes
        partition_nodes = set()
        for scc_idx in successor_closed_sccs:
            partition_nodes.update(sccs_all[scc_idx])
        
        partitions[leaf_scc_idx] = partition_nodes
        partition_labels[leaf_scc_idx] = extract_node_name(sorted(sccs_all[leaf_scc_idx])[0])
    
    # Merge partitions with identical node sets
    merged_partitions, merged_labels, node_set_to_anchors = _merge_partitions(
        partitions, partition_labels, sccs_all, anchor_type="leaf"
    )
    
    print(f"Found {len(sccs_all)} SCCs (including trivial ones)")
    print(f"Found {len(leaf_sccs)} leaf SCCs in condensed graph")
    print(f"Computed {len(partitions)} initial leaf-based partitions")
    print(f"Merged into {len(merged_partitions)} unique partitions")
    
    # Print partition statistics
    for partition_idx, nodes in merged_partitions.items():
        leaf_scc_nodes = set()
        for frozen_nodes, leaf_indices in node_set_to_anchors.items():
            if leaf_indices[0] == partition_idx:
                for idx in leaf_indices:
                    leaf_scc_nodes.update(sccs_all[idx])
                break
        nodes_without_leafs = nodes - leaf_scc_nodes
        print(f"  Partition {merged_labels[partition_idx]}: {len(nodes_without_leafs)} nodes (+ {len(leaf_scc_nodes)} leaf)")
    
    stats = {
        'initial_count': len(partitions),
        'merged_count': len(merged_partitions),
        'strategy': 'Merge only if fully identical'
    }
    
    return sccs_all, scc_map_all, merged_partitions, merged_labels, condensed, stats


def update_node_colors_for_graph_structure(net):
    """Identify and color leaf and source nodes based on graph structure."""
    all_edges = net.edges
    all_node_ids = {node['id'] for node in net.nodes}
    nodes_with_outgoing = {edge['from'] for edge in all_edges}
    nodes_with_incoming = {edge['to'] for edge in all_edges}
    
    leaf_nodes = all_node_ids - nodes_with_outgoing
    source_nodes = all_node_ids - nodes_with_incoming
    
    # Update node colors for leaf and source nodes
    for node in net.nodes:
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
