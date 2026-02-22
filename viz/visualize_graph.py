#!/usr/bin/env python3
"""
Generate PyVis graph showing LET definition dependencies from MFOTL formula JSON.
Each predicate node is used only once and reused across different definitions.
"""

import json
import os
import shutil
import argparse
import re
from pyvis.network import Network
import networkx as nx

from utils.extraction import (
 extract_let_definitions_normal, extract_top_level_rules
)
from utils.config import PHYSICS_OPTIONS
from utils.graph import (
    compute_backward_partitions, expand_rules, add_rule_nodes, add_rule_edges, filter_polarity_edges
)
from utils.html import (
    build_edge_controls_html, build_checkbox_items_html, build_partition_controls_html,
    load_and_populate_template, inject_widget_into_graph_html, configure_isolated_node_physics
)
from utils.mfotl_parser import generate_partition_mfotl_files


def create_graph(json_file, output_file, filter_polarity=False, merge_strategy=None, mfotl_file=None, output_dir='partition_output'):
    """Create PyVis graph from formula JSON showing causality rules.
    
    Args:
        json_file: Path to input JSON file
        output_file: Path to output HTML file (basename only, will be placed in output_dir)
        filter_polarity: Whether to filter polarity edges
        merge_strategy: Partition merging strategy ('by_descendants' or 'no_merge') - required
        mfotl_file: Optional path to MFOTL file for generating partition files
        output_dir: Directory where all output files will be saved (default: 'partition_output')
    """
    
    if merge_strategy is None:
        raise ValueError("merge_strategy is required")
    
    # Delete output directory if it exists to ensure clean run
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    # Create fresh output directory
    os.makedirs(output_dir)
    
    # Construct full output path
    full_output_path = os.path.join(output_dir, os.path.basename(output_file))
    
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
    
    # Expand rules once (resolves LET definitions)
    expanded_rules = expand_rules(rules, let_definitions_dict)
    
    # Add nodes and edges using expanded rules
    node_count = add_rule_nodes(net, expanded_rules)
    print(f"Created {node_count} nodes for rules")
    node_id_to_label = {node['id']: node.get('label', node['id']) for node in net.nodes}
    edge_count = add_rule_edges(net, expanded_rules)
    print(f"Created {edge_count} edges between rules")
    
    # Filter polarity edges if requested
    if filter_polarity:
        removed_count = filter_polarity_edges(net, expanded_rules)
    
    # Configure isolated nodes with low mass for peripheral positioning
    configure_isolated_node_physics(net)
    
    # Compute backward-reachable partitions and mark source/leaf SCCs
    nontrivial_sccs, node_to_scc_map, partitions, partition_labels, stats, leaf_nodes, source_nodes = compute_backward_partitions(
        net, node_id_to_label, merge_strategy=merge_strategy
    )
    
    # Save the graph
    net.save_graph(full_output_path)
    
    # Prepare data for HTML template
    # Create mapping of node IDs to display labels for checkboxes
    all_node_ids = sorted([rule['id'] for rule in rules])
    
    leaf_node_names_json = json.dumps(list(leaf_nodes))
    source_node_names_json = json.dumps(list(source_nodes))
    node_to_scc_map_json = json.dumps(node_to_scc_map)
    nontrivial_sccs_json = json.dumps(nontrivial_sccs)
    
    # Prepare partition data (convert sets to lists for JSON serialization)
    partitions_json = json.dumps({str(k): list(v) for k, v in partitions.items()})
    partition_labels_json = json.dumps({str(k): v for k, v in partition_labels.items()})
    stats_json = json.dumps(stats)
    node_id_to_label_json = json.dumps(node_id_to_label)
    
    # Load template and generate HTML components
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_file = os.path.join(script_dir, 'graph_template.html')
    
    checkbox_items_html = build_checkbox_items_html(all_node_ids, nontrivial_sccs, node_id_to_label)
    edge_controls_html = build_edge_controls_html(False)  # No LET edges in rule mode
    partition_controls_html = build_partition_controls_html(partitions, partition_labels)
    
    # Populate template with data
    widget_html = load_and_populate_template(
        template_file, edge_controls_html, checkbox_items_html,
        leaf_node_names_json, source_node_names_json,
        node_to_scc_map_json, nontrivial_sccs_json, partitions_json, partition_labels_json,
        partition_controls_html, stats_json, filter_polarity, node_id_to_label_json
    )
    
    # Inject widget into generated graph HTML
    inject_widget_into_graph_html(full_output_path, widget_html)
    
    print(f"Graph saved to {full_output_path}")
    
    # Generate minimal MFOTL files for each partition if MFOTL file is provided
    if mfotl_file:
        base_name = os.path.splitext(os.path.basename(mfotl_file))[0]
        generate_partition_mfotl_files(mfotl_file, partitions, partition_labels, rules, output_dir, base_name)
    
    return full_output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generate PyVis graph from MFOTL formula JSON',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input', help='Input JSON file')
    parser.add_argument('output', help='Output HTML file (basename only, will be placed in output directory)')
    parser.add_argument('--output-dir', type=str, default='partition_output',
                       help='Output directory for all generated files (default: partition_output)')
    parser.add_argument('--mfotl', type=str, help='Path to MFOTL file for generating partition files')
    parser.add_argument('--filter-polarity', action='store_true',
                       help='Filter out polarity edges (CauByCau+monotonic, CauBySup+antimonotonic)')
    parser.add_argument('--merge-strategy', type=str, required=True,
                       choices=['by_descendants', 'no_merge'],
                       help='''Partition merging strategy (required):
  no_merge       - Keep all partitions separate without any merging.
  by_descendants - Merge partitions with identical descendant nodes
                   (excluding anchor leaf nodes). 
                    ''')
    args = parser.parse_args()
    
    create_graph(args.input, args.output, 
                filter_polarity=args.filter_polarity,
                merge_strategy=args.merge_strategy,
                mfotl_file=args.mfotl,
                output_dir=args.output_dir)
