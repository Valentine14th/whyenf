#!/usr/bin/env python3
"""
Generate PyVis graph showing LET definition dependencies from MFOTL formula JSON.
Each predicate node is used only once and reused across different definitions.
Supports both original and normal mode for different JSON formats.
"""

import json
import os
import argparse
from pyvis.network import Network
import networkx as nx

from utils.extraction import (
    extract_predicates, extract_let_definitions, extract_implications,
    extract_causality_rules, extract_let_definitions_normal
)
from utils.config import PHYSICS_OPTIONS
from utils.graph import (
    get_node_id, extract_node_name, add_predicate_nodes, add_let_definition_nodes,
    add_let_definition_edges, add_causality_edges, add_implication_edges,
    update_node_colors_for_graph_structure, print_graph_statistics, compute_backward_partitions
)
from utils.html import (
    build_edge_controls_html, build_checkbox_items_html, build_partition_controls_html,
    load_and_populate_template, inject_widget_into_graph_html
)


def create_graph(json_file, output_file, mode="original"):
    """Create PyVis graph from formula JSON showing LET definition dependencies or causality rules."""
    
    # Load JSON
    with open(json_file, 'r') as f:
        formula = json.load(f)
    
    # Extract data based on mode
    if mode == "normal":
        # Normal mode: extract LET definitions from 'lets' field
        definitions = []
        if "lets" in formula:
            definitions = extract_let_definitions_normal(formula["lets"])
            print(f"Found {len(definitions)} LET definitions")
        
        # Extract causality rules and implications only from 'instrs' field
        rules = []
        implications = []
        if "instrs" in formula:
            rules = extract_causality_rules(formula["instrs"])
            implications = extract_implications(formula["instrs"])
        print(f"Found {len(rules)} causality rules (CauByCau and CauBySup)")
        print(f"Found {len(implications)} implications")
    else:
        # Original mode: extract LET definitions
        definitions = extract_let_definitions(formula)
        print(f"Found {len(definitions)} LET definitions")
        
        # Extract all implications
        implications = extract_implications(formula)
        print(f"Found {len(implications)} implications")
        
        rules = []
    
    # Create network and configure physics
    net = Network(height="900px", width="100%", directed=True, 
                  notebook=False, bgcolor="#ffffff", font_color="#333333")
    net.set_options(json.dumps(PHYSICS_OPTIONS))
    
    # Collect all unique predicates from different sources
    let_predicates = set()
    for defn in definitions:
        let_predicates.update(defn["predicates"])
    
    implication_predicates = set()
    for imp in implications:
        implication_predicates.update(imp["left"])
        implication_predicates.update(imp["right"])
    
    causality_predicates = set()
    for rule in rules:
        causality_predicates.update(rule["filter"])
        causality_predicates.update(rule["effects"])
    
    # Collect LET definition names
    let_definition_names = set(defn['name'] for defn in definitions)
    
    # Only create predicate nodes for names that are NOT LET definitions
    if mode == "normal":
        predicate_only_names = (let_predicates | implication_predicates | causality_predicates) - let_definition_names
    else:
        predicate_only_names = (let_predicates | implication_predicates) - let_definition_names
    
    print(f"Found {len(let_predicates)} predicates in LET definitions")
    print(f"Found {len(implication_predicates)} predicates in implications")
    if mode == "normal":
        print(f"Found {len(causality_predicates)} predicates in causality rules")
    print(f"Found {len(let_definition_names)} LET definitions")
    print(f"Found {len(predicate_only_names)} unique predicate nodes (excluding LET definition names)")
    
    # Add nodes to the network
    add_predicate_nodes(net, predicate_only_names, let_predicates, implication_predicates, 
                       causality_predicates, let_definition_names)
    add_let_definition_nodes(net, definitions)
    
    # Add edges to the network
    edge_count = add_let_definition_edges(net, definitions, let_definition_names)
    if definitions:
        print(f"Created {edge_count} edges from LET definitions")
    
    causality_edge_count = 0
    if mode == "normal":
        causality_edge_count = add_causality_edges(net, rules, let_definition_names)
        print(f"Created {causality_edge_count} unique edges from {len(rules)} causality rules")
    
    implication_edge_count = add_implication_edges(net, implications, let_definition_names)
    print(f"Created {implication_edge_count} unique edges from {len(implications)} implications")

    # Compute backward-reachable partitions
    sccs_all, scc_map_all, partitions, partition_labels, condensed, stats = compute_backward_partitions(net)
    
    # Filter SCCs to only non-trivial ones (size > 1) for visualization
    sccs = [scc for scc in sccs_all if len(scc) > 1]
    scc_map = {node_id: idx for idx, scc in enumerate(sccs) for node_id in scc}
    
    # Update node colors based on graph structure (leaf/source nodes)
    leaf_nodes, source_nodes = update_node_colors_for_graph_structure(net)
    print(f"Found {len(leaf_nodes)} leaf nodes (no outgoing edges)")
    print(f"Found {len(source_nodes)} source nodes (no incoming edges)")
    
    # Save the graph
    net.save_graph(output_file)
    
    # Prepare data for HTML template
    all_node_names = sorted(list(predicate_only_names) + [defn['name'] for defn in definitions])
    leaf_node_names_json = json.dumps([extract_node_name(nid) for nid in leaf_nodes])
    source_node_names_json = json.dumps([extract_node_name(nid) for nid in source_nodes])
    scc_map_json = json.dumps(scc_map)
    sccs_json = json.dumps(sccs)
    
    # Prepare partition data (convert sets to lists for JSON serialization)
    partitions_json = json.dumps({str(k): list(v) for k, v in partitions.items()})
    partition_labels_json = json.dumps({str(k): v for k, v in partition_labels.items()})
    stats_json = json.dumps(stats)
    
    # Load template and generate HTML components
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_file = os.path.join(script_dir, 'graph_template.html')
    
    checkbox_items_html = build_checkbox_items_html(all_node_names)
    edge_controls_html = build_edge_controls_html(mode, len(definitions) > 0)
    partition_controls_html = build_partition_controls_html(partitions, partition_labels)
    
    # Populate template with data
    widget_html = load_and_populate_template(
        template_file, edge_controls_html, checkbox_items_html,
        leaf_node_names_json, source_node_names_json,
        scc_map_json, sccs_json, partitions_json, partition_labels_json,
        partition_controls_html, stats_json
    )
    
    # Inject widget into generated graph HTML
    inject_widget_into_graph_html(output_file, widget_html)
    
    print(f"Graph saved to {output_file}")
    
    # Print statistics
    print_graph_statistics(definitions, predicate_only_names, edge_count, 
                          implications, implication_edge_count, rules, 
                          causality_edge_count, mode)
    
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate PyVis graph from MFOTL formula JSON')
    parser.add_argument('input', help='Input JSON file')
    parser.add_argument('output', help='Output HTML file (will be created in viz/ directory)')
    parser.add_argument('--normal', action='store_true', 
                       help='Process normal mode JSON (with CauByCau/CauBySup instead of simple implications)')
    
    args = parser.parse_args()
    
    mode = "normal" if args.normal else "original"
    
    # Force output to be in viz directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_basename = os.path.basename(args.output)
    output_path = os.path.join(script_dir, output_basename)
    
    create_graph(args.input, output_path, mode=mode)
