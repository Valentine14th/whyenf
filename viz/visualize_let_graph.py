#!/usr/bin/env python3
"""
Generate PyVis graph showing LET definition dependencies from MFOTL formula JSON.
Each predicate node is used only once and reused across different definitions.
Supports both original and normal mode for different JSON formats.
"""

import json
import sys
import os
import argparse
import webbrowser
from pyvis.network import Network


def extract_predicates(node, predicates_set=None):
    """Recursively extract all predicate names from a formula node."""
    if predicates_set is None:
        predicates_set = set()
    
    if isinstance(node, list):
        for item in node:
            extract_predicates(item, predicates_set)
        return predicates_set
    
    if not isinstance(node, dict):
        return predicates_set
    
    # Check if this is a Predicate constructor
    if node.get("constructor") == "Predicate":
        predicates_set.add(node["name"])
    
    # Recursively traverse all values in the dictionary
    for value in node.values():
        if isinstance(value, (dict, list)):
            extract_predicates(value, predicates_set)
    
    return predicates_set


def extract_let_definitions(node, definitions=None):
    """Extract all LET definitions with their predicates."""
    if definitions is None:
        definitions = []
    
    if not isinstance(node, dict):
        return definitions
    
    if node.get("constructor") == "Let":
        definitions.append({
            "name": node.get("name", "Unknown"),
            "type": node.get("type", ""),
            "predicates": extract_predicates(node.get("body", {}))
        })
        # Continue in the "in" clause
        extract_let_definitions(node.get("in"), definitions)
    else:
        # Recursively search in all dict/list values
        for value in node.values():
            if isinstance(value, (dict, list)):
                extract_let_definitions(value, definitions)
    
    return definitions


def extract_implications(node, implications=None):
    """Extract all implications (Imp) from formula with predicates on left and right."""
    if implications is None:
        implications = []
    
    if isinstance(node, list):
        for item in node:
            extract_implications(item, implications)
        return implications
    
    if not isinstance(node, dict):
        return implications
    
    if node.get("constructor") == "Imp":
        implications.append({
            "left": extract_predicates(node.get("left", {})),
            "right": extract_predicates(node.get("right", {}))
        })
    
    # Recursively search in all dict/list values
    for value in node.values():
        if isinstance(value, (dict, list)):
            extract_implications(value, implications)
    
    return implications


def extract_let_definitions_normal(lets_array):
    """Extract LET definitions from normal JSON format (from 'lets' array)."""
    return [{
        "name": let_def.get("e", "Unknown"),
        "type": let_def.get("enftype", ""),
        "predicates": extract_predicates(let_def.get("formula", {}))
    } for let_def in lets_array]


def extract_causality_rules(node, rules=None):
    """Extract all CauByCau and CauBySup rules with predicates from filter and effects."""
    if rules is None:
        rules = []
    
    if isinstance(node, list):
        for item in node:
            extract_causality_rules(item, rules)
        return rules
    
    if not isinstance(node, dict):
        return rules
    
    constructor = node.get("constructor")
    if constructor in ["CauByCau", "CauBySup"]:
        by_field = node.get("by", {})
        rules.append({
            "type": constructor,
            "filter": extract_predicates(by_field.get("filter", {})),
            "effects": extract_predicates(by_field.get("effects", {}))
        })
    
    # Recursively search in all dict/list values
    for value in node.values():
        if isinstance(value, (dict, list)):
            extract_causality_rules(value, rules)
    
    return rules


# ============================================================================
# Helper Functions
# ============================================================================

def get_node_id(pred_name, let_definition_names):
    """Return the correct node ID (LET node or predicate node)."""
    return f"LET_{pred_name}" if pred_name in let_definition_names else pred_name


def extract_node_name(node_id):
    """Extract node name without LET_ prefix."""
    return node_id[4:] if node_id.startswith('LET_') else node_id


def get_physics_options():
    """Return network physics configuration as a dict."""
    return {
        "physics": {
            "enabled": True,
            "barnesHut": {
                "gravitationalConstant": -5000,
                "centralGravity": 0.1,
                "springLength": 150,
                "springConstant": 0.01,
                "damping": 0.9,
                "avoidOverlap": 0.2
            },
            "stabilization": {
                "enabled": True,
                "iterations": 1000,
                "updateInterval": 50
            },
            "maxVelocity": 15,
            "minVelocity": 0.1,
            "solver": "barnesHut",
            "timestep": 0.3
        },
        "nodes": {
            "font": {
                "size": 16,
                "face": "Arial",
                "bold": {"color": "#333333"}
            },
            "borderWidth": 2,
            "borderWidthSelected": 3,
            "shadow": {"enabled": False},
            "physics": True
        },
        "edges": {
            "arrows": {
                "to": {"enabled": True, "scaleFactor": 0.6}
            },
            "smooth": {"enabled": False},
            "width": 1.5,
            "shadow": {"enabled": False}
        },
        "interaction": {
            "hover": True,
            "tooltipDelay": 100,
            "hideEdgesOnDrag": True,
            "hideNodesOnDrag": False,
            "navigationButtons": True,
            "keyboard": {"enabled": True}
        }
    }


def get_predicate_node_color():
    """Return color scheme for predicate nodes."""
    return {
        "border": "#2980b9",
        "background": "#5dade2",
        "highlight": {"border": "#f39c12", "background": "#f1c40f"}
    }


def get_let_node_color():
    """Return color scheme for LET definition nodes."""
    return {
        "border": "#c0392b",
        "background": "#ec7063",
        "highlight": {"border": "#d68910", "background": "#f39c12"}
    }


def get_leaf_color(is_let_node):
    """Return color scheme for leaf nodes (no outgoing edges)."""
    if is_let_node:
        return {
            "border": "#943126",
            "background": "#cd6155",
            "highlight": {"border": "#d68910", "background": "#f39c12"}
        }
    return {
        "border": "#5d6d7e",
        "background": "#85929e",
        "highlight": {"border": "#f39c12", "background": "#f1c40f"}
    }


def get_source_color(is_let_node):
    """Return color scheme for source nodes (no incoming edges)."""
    if is_let_node:
        return {
            "border": "#d68910",
            "background": "#f39c12",
            "highlight": {"border": "#d68910", "background": "#f39c12"}
        }
    return {
        "border": "#7d3c98",
        "background": "#af7ac5",
        "highlight": {"border": "#f39c12", "background": "#f1c40f"}
    }


def get_causality_color(rule_types):
    """Determine edge color based on causality rule types."""
    if rule_types == {"CauByCau"}:
        return "#27ae60"  # Green
    elif rule_types == {"CauBySup"}:
        return "#3498db"  # Blue
    else:
        return "#9b59b6"  # Purple (mixed)


def calculate_edge_properties(count, base_width=1.5, base_opacity=0.5, 
                             width_increment=0.5, opacity_increment=0.1, 
                             max_width=6, max_opacity=0.95):
    """Calculate edge width and opacity based on count."""
    width = min(base_width + (count - 1) * width_increment, max_width)
    opacity = min(base_opacity + (count - 1) * opacity_increment, max_opacity)
    return width, opacity


def create_edge_control(control_id, label, color=None, checked=True):
    """Create a single edge control HTML element."""
    checked_attr = ' checked' if checked else ''
    indicator_style = f' style="background: {color};"' if color else ' class="implication"'
    return (
        f'<label><input type="checkbox" id="{control_id}"{checked_attr} />'
        f'<span class="edge-label"><span class="edge-indicator"{indicator_style}>'
        f'</span>{label}</span></label>'
    )


def build_edge_controls_html(mode, has_definitions):
    """Build edge controls HTML based on mode and available edge types."""
    controls = []
    
    # LET/Definition edges
    if mode == "original" or (mode == "normal" and has_definitions):
        controls.append(create_edge_control("show-let-edges", "Definition Edges", "#bdc3c7"))
    
    # Implication edges (not in normal mode)
    if mode != "normal":
        controls.append(create_edge_control("show-implication-edges", "Implication Edges"))
    
    # Causality edges (normal mode only)
    if mode == "normal":
        controls.append(create_edge_control("show-caubycau-edges", "Cause by Causing Edges", "#27ae60"))
        controls.append(create_edge_control("show-caubysup-edges", "Cause by Suppressing Edges", "#3498db"))
    
    return '\n                '.join(controls)


def build_checkbox_items_html(node_names):
    """Build checkbox items HTML for node selection."""
    items = []
    for i, name in enumerate(node_names):
        items.append(
            f'<div class="checkbox-item">\n'
            f'    <input type="checkbox" id="node_{i}" value="{name}" />\n'
            f'    <label for="node_{i}">{name}</label>\n'
            f'</div>'
        )
    return '\n                '.join(items)


def create_let_graph(json_file, output_file, mode="original"):
    """Create PyVis graph from formula JSON showing LET definition dependencies or causality rules."""
    
    # Load JSON
    with open(json_file, 'r') as f:
        formula = json.load(f)
    
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
    net.set_options(json.dumps(get_physics_options()))
    
    # Collect all unique predicates from LET definitions (original mode only)
    let_predicates = set()
    for defn in definitions:
        let_predicates.update(defn["predicates"])
    
    # Collect LET definition names
    let_definition_names = set(defn['name'] for defn in definitions)
    
    # Collect all unique predicates from implications
    implication_predicates = set()
    for imp in implications:
        implication_predicates.update(imp["left"])
        implication_predicates.update(imp["right"])
    
    # Collect all unique predicates from causality rules (normal mode)
    causality_predicates = set()
    for rule in rules:
        causality_predicates.update(rule["filter"])
        causality_predicates.update(rule["effects"])
    
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
    
    # Helper function to build predicate title
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
    
    # Add predicate nodes (blue circles)
    for pred in predicate_only_names:
        net.add_node(
            pred,
            label=pred,
            color=get_predicate_node_color(),
            shape="dot",
            size=25,
            font={"size": 14, "color": "#2c3e50"},
            title=build_predicate_title(pred)
        )
    
    # Add LET definition nodes (red boxes)
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
            color=get_let_node_color(),
            shape="box",
            size=30,
            font={"size": 15, "color": "#ffffff", "bold": True},
            shapeProperties={"borderRadius": 6},
            title=hover_text
        )
    
    # Add edges from LET definitions to their predicates
    edge_count = 0
    for defn in definitions:
        let_id = f"LET_{defn['name']}"
        for pred in defn["predicates"]:
            net.add_edge(
                get_node_id(pred, let_definition_names),
                let_id,
                color={"color": "#bdc3c7", "highlight": "#e67e22", "opacity": 0.6},
                width=2,
                title=f"{pred} used by {defn['name']}"
            )
            edge_count += 1
    
    if definitions:
        print(f"Created {edge_count} edges from LET definitions")
    
    # Add edges from causality rules (normal mode only)
    causality_edge_count = 0
    if mode == "normal":
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
            causality_edge_count += 1
        
        print(f"Created {causality_edge_count} unique edges from {len(rules)} causality rules")
    
    # Add edges from implications
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
    implication_edge_count = 0
    for (left_node, right_node), count in implication_edges.items():
        width, opacity = calculate_edge_properties(count, base_width=1.5, base_opacity=0.5, max_width=5)
        plural = "implications" if count > 1 else "implication"
        
        net.add_edge(
            left_node,
            right_node,
            color={"color": "#9b59b6", "highlight": "#e74c3c", "opacity": opacity},
            width=width,
            dashes=[5, 5],
            title=f"Implication: {left_node} → {right_node}\n({count} {plural})"
        )
        implication_edge_count += 1
    
    print(f"Created {implication_edge_count} unique edges from {len(implications)} implications")
    
    # Identify and color leaf and source nodes
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
            node['color'] = get_leaf_color(is_let_node)
        elif node['id'] in source_nodes:
            node['color'] = get_source_color(is_let_node)
    
    print(f"Found {len(leaf_nodes)} leaf nodes (no outgoing edges)")
    print(f"Found {len(source_nodes)} source nodes (no incoming edges)")
    
    # Save the graph and add search functionality
    net.save_graph(output_file)
    
    # Prepare node names for dropdown
    all_node_names = sorted(list(predicate_only_names) + [defn['name'] for defn in definitions])
    leaf_node_names_json = json.dumps([extract_node_name(nid) for nid in leaf_nodes])
    source_node_names_json = json.dumps([extract_node_name(nid) for nid in source_nodes])
    
    # Load template file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_file = os.path.join(script_dir, 'graph_template.html')
    
    with open(template_file, 'r') as f:
        widget_template = f.read()
    
    # Build HTML components
    checkbox_items_html = build_checkbox_items_html(all_node_names)
    edge_controls_html = build_edge_controls_html(mode, len(definitions) > 0)
    
    # Replace placeholders in template
    widget_html = (widget_template
                   .replace('<!-- EDGE_CONTROLS_PLACEHOLDER -->', edge_controls_html)
                   .replace('<!-- CHECKBOX_ITEMS_PLACEHOLDER -->', checkbox_items_html)
                   .replace('<!-- LEAF_NODES_JSON -->', leaf_node_names_json)
                   .replace('<!-- SOURCE_NODES_JSON -->', source_node_names_json))
    
    # Read the generated graph HTML and insert widget
    with open(output_file, 'r') as f:
        html_content = f.read()
    
    # Insert widget before closing body tag
    html_content = html_content.replace('</body>', widget_html + '</body>')
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Graph saved to {output_file}")
    
    # Print statistics
    total_nodes = len(predicate_only_names) + len(definitions)
    print(f"\nGraph Statistics:")
    print(f"  Nodes:")
    print(f"    - LET definitions: {len(definitions)}")
    print(f"    - Unique predicates: {len(predicate_only_names)}")
    print(f"    - Total nodes: {total_nodes}")
    print(f"  Edges:")
    if mode == "original" and definitions:
        print(f"    - LET definition edges: {edge_count}")
    if mode == "normal":
        print(f"    - Causality rules: {len(rules)}")
        print(f"    - Causality edges: {causality_edge_count}")
    print(f"    - Implications: {len(implications)}")
    print(f"    - Implication edges: {implication_edge_count}")
    if mode == "original" and definitions:
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
    
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate PyVis graph from MFOTL formula JSON')
    parser.add_argument('input', help='Input JSON file')
    parser.add_argument('output', help='Output HTML file (will be created in viz/ directory)')
    parser.add_argument('--normal', action='store_true', 
                       help='Process normal mode JSON (with CauByCau/CauBySup instead of LET definitions)')
    
    args = parser.parse_args()
    
    mode = "normal" if args.normal else "original"
    
    # Force output to be in viz directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_basename = os.path.basename(args.output)
    output_path = os.path.join(script_dir, output_basename)
    
    html_file = create_let_graph(args.input, output_path, mode=mode)
    
    # Open in browser
    abs_path = os.path.abspath(html_file)
    print(f"\nOpening {abs_path} in browser...")
    webbrowser.open('file://' + abs_path)
