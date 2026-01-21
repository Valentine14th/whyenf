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
    extract_causality_rules, extract_let_definitions_normal, extract_top_level_rules
)
from utils.config import PHYSICS_OPTIONS
from utils.graph import (
    get_node_id, extract_node_name, add_predicate_nodes, add_let_definition_nodes,
    add_let_definition_edges, add_causality_edges, add_implication_edges,
    find_source_and_leaf_nodes, print_graph_statistics, compute_backward_partitions
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
    
    # Extract top-level rules from instructions
    rules = []
    if "instrs" in formula:
        rules = extract_top_level_rules(formula["instrs"])
        print(f"Found {len(rules)} top-level rules")
    
    # Extract LET definitions
    let_definitions_dict = {}
    if "lets" in formula:
        let_definitions_dict = extract_let_definitions_normal(formula["lets"])
        print(f"Found {len(let_definitions_dict)} LET definitions")
    
    # Create network and configure physics
    net = Network(height="900px", width="100%", directed=True, 
                  notebook=False, bgcolor="#ffffff", font_color="#333333")
    net.set_options(json.dumps(PHYSICS_OPTIONS))
    
    # Add rule nodes
    from utils.graph import add_rule_nodes, add_rule_edges
    add_rule_nodes(net, rules)
    
    # Add edges between rules
    edge_count = add_rule_edges(net, rules, let_definitions_dict)
    print(f"Created {edge_count} edges between rules")
    
    # Compute backward-reachable partitions
    sccs_all, scc_map_all, partitions, partition_labels, condensed, stats = compute_backward_partitions(net)
    
    # Filter SCCs to only non-trivial ones (size > 1) for visualization
    sccs = [scc for scc in sccs_all if len(scc) > 1]
    scc_map = {node_id: idx for idx, scc in enumerate(sccs) for node_id in scc}
    
    # Update node colors based on graph structure (leaf/source nodes)
    leaf_nodes, source_nodes = find_source_and_leaf_nodes(net)
    print(f"Found {len(leaf_nodes)} leaf nodes (no outgoing edges)")
    print(f"Found {len(source_nodes)} source nodes (no incoming edges)")
    
    # Save the graph
    net.save_graph(output_file)
    
    # Prepare data for HTML template
    all_node_ids = sorted([rule['id'] for rule in rules])
    leaf_node_names_json = json.dumps(list(leaf_nodes))
    source_node_names_json = json.dumps(list(source_nodes))
    scc_map_json = json.dumps(scc_map)
    sccs_json = json.dumps(sccs)
    
    # Prepare partition data (convert sets to lists for JSON serialization)
    partitions_json = json.dumps({str(k): list(v) for k, v in partitions.items()})
    partition_labels_json = json.dumps({str(k): v for k, v in partition_labels.items()})
    stats_json = json.dumps(stats)
    
    # Load template and generate HTML components
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_file = os.path.join(script_dir, 'graph_template.html')
    
    checkbox_items_html = build_checkbox_items_html(all_node_ids)
    edge_controls_html = build_edge_controls_html(mode, False)  # No LET edges in rule mode
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
