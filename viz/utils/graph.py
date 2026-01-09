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


def compute_backward_reachable_partitions(net):
    """
    Decompose the graph into successor-closed subgraphs.
    
    Each subgraph corresponds to the backward-reachable set of a leaf node 
    in the condensed graph (DAG formed by collapsing SCCs into single nodes).
    
    Returns:
        - sccs_all: List of all SCCs (list of node lists)
        - scc_map_all: Dict mapping node_id to SCC index
        - partitions: Dict mapping leaf SCC index to set of all reachable node IDs
        - partition_labels: Dict mapping leaf SCC index to leaf node name
        - condensed_graph: The condensed NetworkX graph
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
    
    # Find leaf nodes in condensed graph (no outgoing edges)
    leaf_sccs = [node for node in condensed.nodes() if condensed.out_degree(node) == 0]
    
    # For each leaf SCC, compute backward-reachable set
    partitions = {}
    partition_labels = {}
    for leaf_scc_idx in leaf_sccs:
        # Get all SCCs that can reach this leaf SCC (predecessors in DAG)
        reachable_sccs = nx.ancestors(condensed, leaf_scc_idx)
        reachable_sccs.add(leaf_scc_idx)  # Include the leaf itself
        
        # Expand to original nodes
        partition_nodes = set()
        for scc_idx in reachable_sccs:
            partition_nodes.update(sccs_all[scc_idx])
        
        partitions[leaf_scc_idx] = partition_nodes
        
        # Get a representative leaf node name (first node in the leaf SCC)
        leaf_nodes = sccs_all[leaf_scc_idx]
        partition_labels[leaf_scc_idx] = extract_node_name(sorted(leaf_nodes)[0])
    
    print(f"Found {len(sccs_all)} SCCs (including trivial ones)")
    print(f"Found {len(leaf_sccs)} leaf SCCs in condensed graph")
    print(f"Computed {len(partitions)} backward-reachable partitions")
    
    # Print partition statistics
    for leaf_idx, nodes in partitions.items():
        print(f"  Partition {partition_labels[leaf_idx]}: {len(nodes)} nodes")
    
    return sccs_all, scc_map_all, partitions, partition_labels, condensed


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
