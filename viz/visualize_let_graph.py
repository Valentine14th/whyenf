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


def extract_predicates(node, predicates_set):
    """Recursively extract all predicate names from a formula node."""
    if not isinstance(node, dict):
        # If it's a list, recurse into it
        if isinstance(node, list):
            for item in node:
                extract_predicates(item, predicates_set)
        return
    
    # Check if this is a Predicate constructor
    if node.get("constructor") == "Predicate":
        predicates_set.add(node["name"])
        # Don't return - continue to check if there are nested predicates in args
    
    # Recursively traverse all values in the dictionary
    for key, value in node.items():
        if isinstance(value, dict):
            extract_predicates(value, predicates_set)
        elif isinstance(value, list):
            for item in value:
                extract_predicates(item, predicates_set)


def extract_let_definitions(node, definitions=None):
    """Extract all LET definitions with their predicates."""
    if definitions is None:
        definitions = []
    
    if not isinstance(node, dict):
        return definitions
    
    if node.get("constructor") == "Let":
        let_name = node.get("name", "Unknown")
        let_type = node.get("type", "")
        
        # Extract predicates from the body
        predicates = set()
        if "body" in node:
            extract_predicates(node["body"], predicates)
        
        definitions.append({
            "name": let_name,
            "type": let_type,
            "predicates": predicates
        })
        
        # Continue searching in the "in" clause
        if "in" in node:
            extract_let_definitions(node["in"], definitions)
    else:
        # Recursively search for LET definitions
        for key, value in node.items():
            if isinstance(value, dict):
                extract_let_definitions(value, definitions)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        extract_let_definitions(item, definitions)
    
    return definitions


def extract_implications(node, implications=None):
    """Extract all implications (Imp) from formula with predicates on left and right."""
    if implications is None:
        implications = []
    
    # Handle list input
    if isinstance(node, list):
        for item in node:
            extract_implications(item, implications)
        return implications
    
    if not isinstance(node, dict):
        return implications
    
    if node.get("constructor") == "Imp":
        # Extract predicates from left (antecedent)
        left_predicates = set()
        if "left" in node:
            extract_predicates(node["left"], left_predicates)
        
        # Extract predicates from right (consequent)
        right_predicates = set()
        if "right" in node:
            extract_predicates(node["right"], right_predicates)
        
        implications.append({
            "left": left_predicates,
            "right": right_predicates
        })
    
    # Recursively search for implications
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, dict):
                extract_implications(value, implications)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        extract_implications(item, implications)
    
    return implications


def extract_let_definitions_normal(lets_array):
    """Extract LET definitions from normal JSON format (from 'lets' array)."""
    definitions = []
    for let_def in lets_array:
        let_name = let_def.get("e", "Unknown")
        
        # Extract predicates from the formula
        predicates = set()
        if "formula" in let_def:
            extract_predicates(let_def["formula"], predicates)
        
        definitions.append({
            "name": let_name,
            "type": let_def.get("enftype", ""),
            "predicates": predicates
        })
    
    return definitions


def extract_causality_rules(node, rules=None):
    """Extract all CauByCau and CauBySup rules with predicates from filter and effects."""
    if rules is None:
        rules = []
    
    # Handle list input
    if isinstance(node, list):
        for item in node:
            extract_causality_rules(item, rules)
        return rules
    
    if not isinstance(node, dict):
        return rules
    
    constructor = node.get("constructor")
    if constructor in ["CauByCau", "CauBySup"]:
        # Extract predicates from filter (inside "by" field)
        filter_predicates = set()
        if "by" in node and isinstance(node["by"], dict):
            if "filter" in node["by"]:
                extract_predicates(node["by"]["filter"], filter_predicates)
        
        # Extract predicates from effects (inside "by" field)
        effects_predicates = set()
        if "by" in node and isinstance(node["by"], dict):
            if "effects" in node["by"]:
                extract_predicates(node["by"]["effects"], effects_predicates)
        
        rules.append({
            "type": constructor,
            "filter": filter_predicates,
            "effects": effects_predicates
        })
    
    # Recursively search for causality rules
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, dict):
                extract_causality_rules(value, rules)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        extract_causality_rules(item, rules)
    
    return rules


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
    
    # Create network
    net = Network(height="900px", width="100%", directed=True, 
                  notebook=False, bgcolor="#ffffff", font_color="#333333")
    
    # Configure physics for better layout and performance with minimal movement
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -5000,
          "centralGravity": 0.1,
          "springLength": 150,
          "springConstant": 0.01,
          "damping": 0.9,
          "avoidOverlap": 0.2
        },
        "stabilization": {
          "enabled": true,
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
          "bold": {
            "color": "#333333"
          }
        },
        "borderWidth": 2,
        "borderWidthSelected": 3,
        "shadow": {
          "enabled": false
        },
        "physics": true
      },
      "edges": {
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 0.6
          }
        },
        "smooth": {
          "enabled": false
        },
        "width": 1.5,
        "shadow": {
          "enabled": false
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "hideEdgesOnDrag": true,
        "hideNodesOnDrag": false,
        "navigationButtons": true,
        "keyboard": {
          "enabled": true
        }
      }
    }
    """)
    
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
    
    # Add predicate nodes (blue circles) - only for names that aren't LET definitions
    for pred in predicate_only_names:
        in_lets = pred in let_predicates
        in_implications = pred in implication_predicates
        in_causality = pred in causality_predicates
        
        # Build title based on where predicate appears
        title_parts = [f"Predicate: {pred}"]
        locations = []
        if in_lets:
            locations.append("LET definitions")
        if in_implications:
            locations.append("implications")
        if in_causality:
            locations.append("causality rules")
        
        if locations:
            title_parts.append(f"(Used in {' and '.join(locations)})")
        
        net.add_node(pred, 
                    label=pred, 
                    color={"border": "#2980b9", "background": "#5dade2", "highlight": {"border": "#f39c12", "background": "#f1c40f"}},
                    shape="dot",
                    size=25,
                    font={"size": 14, "color": "#2c3e50"},
                    title="\n".join(title_parts))
    
    # Add LET definition nodes (red boxes) - when definitions exist
    if len(definitions) > 0:
        for defn in definitions:
            let_id = f"LET_{defn['name']}"
            label = f"{defn['name']}"
            
            # Add predicates list to hover title
            predicates_list = sorted(defn['predicates'])
            hover_text = f"LET definition: {defn['name']}\nType: {defn['type']}\nUses {len(defn['predicates'])} predicates:\n"
            hover_text += "\n".join(f"  • {p}" for p in predicates_list)
            
            net.add_node(let_id,
                        label=label,
                        color={"border": "#c0392b", "background": "#ec7063", "highlight": {"border": "#d68910", "background": "#f39c12"}},
                        shape="box",
                        size=30,
                        font={"size": 15, "color": "#ffffff", "bold": True},
                        shapeProperties={"borderRadius": 6},
                        title=hover_text)
    
    # Add edges from LET definitions to their predicates
    edge_count = 0
    if len(definitions) > 0:
        for defn in definitions:
            let_id = f"LET_{defn['name']}"
            for pred in defn["predicates"]:
                # Use LET node if predicate name matches a LET definition
                pred_node = f"LET_{pred}" if pred in let_definition_names else pred
                net.add_edge(let_id, pred_node, 
                            color={"color": "#bdc3c7", "highlight": "#e67e22", "opacity": 0.6},
                            width=2,
                            title=f"{defn['name']} uses {pred}")
                edge_count += 1
        
        print(f"Created {edge_count} edges from LET definitions")
    
    # Add edges from causality rules (normal mode only)
    causality_edge_count = 0
    if mode == "normal":
        causality_edges = {}  # (filter_pred, effect_pred) -> (count, rule_types)
        for rule in rules:
            rule_type = rule["type"]
            for filter_pred in rule["filter"]:
                for effect_pred in rule["effects"]:
                    # Use LET nodes if the predicate name matches a LET definition
                    filter_node = f"LET_{filter_pred}" if filter_pred in let_definition_names else filter_pred
                    effect_node = f"LET_{effect_pred}" if effect_pred in let_definition_names else effect_pred
                    edge_key = (filter_node, effect_node)
                    if edge_key not in causality_edges:
                        causality_edges[edge_key] = {"count": 0, "types": set()}
                    causality_edges[edge_key]["count"] += 1
                    causality_edges[edge_key]["types"].add(rule_type)
        
        # Add edges to graph with weight based on count
        for (filter_node, effect_node), data in causality_edges.items():
            count = data["count"]
            rule_types = ", ".join(sorted(data["types"]))
            
            # Scale width and opacity based on count
            width = min(2 + (count - 1) * 0.5, 6)
            opacity = min(0.6 + (count - 1) * 0.1, 0.95)
            
            # Different colors for different causality rule types
            if data["types"] == {"CauByCau"}:
                edge_color = "#27ae60"  # Green for CauByCau
            elif data["types"] == {"CauBySup"}:
                edge_color = "#3498db"  # Blue for CauBySup
            else:
                edge_color = "#9b59b6"  # Purple for mixed (both CauByCau and CauBySup)
            
            plural = "rules" if count > 1 else "rule"
            net.add_edge(filter_node, effect_node,
                        color={"color": edge_color, "highlight": "#f39c12", "opacity": opacity},
                        width=width,
                        title=f"Causality: {filter_node} → {effect_node}\n({count} {plural}: {rule_types})")
            causality_edge_count += 1
        
        print(f"Created {causality_edge_count} unique edges from {len(rules)} causality rules")
    
    # Add edges from implications (left predicates -> right predicates)
    # Track edge counts to show weight
    # Helper function to get correct node ID
    def get_node_id(pred_name):
        # If predicate name matches a LET definition, use the LET node
        if pred_name in let_definition_names:
            return f"LET_{pred_name}"
        return pred_name
    
    implication_edges = {}  # (left, right) -> count
    for imp in implications:
        for left_pred in imp["left"]:
            for right_pred in imp["right"]:
                # Use LET nodes if the predicate name matches a LET definition
                left_node = get_node_id(left_pred)
                right_node = get_node_id(right_pred)
                edge_key = (left_node, right_node)
                implication_edges[edge_key] = implication_edges.get(edge_key, 0) + 1
    
    # Add edges to graph with weight based on count
    implication_edge_count = 0
    for (left_node, right_node), count in implication_edges.items():
        # Scale width and opacity based on count (min 1.5, scales up to 5)
        width = min(1.5 + (count - 1) * 0.5, 5)
        opacity = min(0.5 + (count - 1) * 0.1, 0.95)
        
        plural = "implications" if count > 1 else "implication"
        net.add_edge(left_node, right_node,
                    color={"color": "#9b59b6", "highlight": "#e74c3c", "opacity": opacity},
                    width=width,
                    dashes=[5, 5],  # Dashed line to distinguish from LET edges
                    title=f"Implication: {left_node} → {right_node}\n({count} {plural})")
        implication_edge_count += 1
    
    print(f"Created {implication_edge_count} unique edges from {len(implications)} implications")
    
    # Save the graph and add search functionality
    net.save_graph(output_file)
    
    # Prepare node list for dropdown (only predicate nodes, not LET nodes)
    all_nodes = sorted(list(predicate_only_names))
    let_nodes = sorted([defn['name'] for defn in definitions])
    all_node_names = sorted(all_nodes + let_nodes)
    
    # Load external CSS and JS files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    css_file = os.path.join(script_dir, 'graph_search_widget.css')
    js_file = os.path.join(script_dir, 'graph_search_widget.js')
    
    with open(css_file, 'r') as f:
        css_content = f.read()
    
    with open(js_file, 'r') as f:
        js_content = f.read()
    
    # Build checkbox items HTML
    checkbox_items_html = ''.join(
        f'                <div class="checkbox-item">\n'
        f'                    <input type="checkbox" id="node_{i}" value="{name}" />\n'
        f'                    <label for="node_{i}">{name}</label>\n'
        f'                </div>\n'
        for i, name in enumerate(all_node_names)
    )
    
    # Build complete search HTML
    search_html = f"""
    <style>
        {css_content}
    </style>
    
    <div id="search-container">
        <div id="search-header">
            <span id="search-label">Select Events/Definitions</span>
            <button id="toggle-btn">Hide</button>
        </div>
        <div id="search-content">
            <div id="edge-controls">
                {'<label><input type="checkbox" id="show-let-edges" checked /><span class="edge-label"><span class="edge-indicator let"></span>LET Definition Edges</span></label>' if mode == "original" else ''}
                {'<label><input type="checkbox" id="show-let-edges" checked /><span class="edge-label"><span class="edge-indicator" style="background: #bdc3c7;"></span>LET Edges</span></label>' if mode == "original" or (mode == "normal" and len(definitions) > 0) else ''}
                <label>
                    <input type="checkbox" id="show-implication-edges" checked />
                    <span class="edge-label">
                        <span class="edge-indicator implication"></span>
                        Implication Edges
                    </span>
                </label>
                {'<label><input type="checkbox" id="show-caubycau-edges" checked /><span class="edge-label"><span class="edge-indicator" style="background: #27ae60;"></span>CauByCau Edges</span></label>' if mode == "normal" else ''}
                {'<label><input type="checkbox" id="show-caubysup-edges" checked /><span class="edge-label"><span class="edge-indicator" style="background: #3498db;"></span>CauBySup Edges</span></label>' if mode == "normal" else ''}
            </div>
            <div id="selection-controls">
                <label>
                    <input type="checkbox" id="show-all-neighborhood-edges" />
                    <span class="edge-label">Show all edges in neighborhood</span>
                </label>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #c8e6c9;">
                    <div style="font-size: 11px; color: #555; margin-bottom: 5px;">Edge direction:</div>
                    <label style="margin-bottom: 3px;">
                        <input type="radio" name="edge-direction" value="both" checked />
                        <span class="edge-label">Both</span>
                    </label>
                    <label style="margin-bottom: 3px;">
                        <input type="radio" name="edge-direction" value="outgoing" />
                        <span class="edge-label">Outgoing only</span>
                    </label>
                    <label style="margin-bottom: 3px;">
                        <input type="radio" name="edge-direction" value="incoming" />
                        <span class="edge-label">Incoming only</span>
                    </label>
                </div>
            </div>
            <input type="text" id="search-input" placeholder="Filter by name..." />
            <div id="dropdown-list">
{checkbox_items_html}
            </div>
            <div id="selected-nodes"></div>
            <div id="button-container">
                <button class="btn btn-clear" id="btn-clear">Clear All</button>
            </div>
            <div id="search-results"></div>
        </div>
    </div>
    
    <script type="text/javascript">
        {js_content}
    </script>
    """
    
    # Add custom search box HTML/JS
    with open(output_file, 'r') as f:
        html_content = f.read()
    
    # Insert before closing body tag
    html_content = html_content.replace('</body>', search_html + '</body>')
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Graph saved to {output_file}")
    
    # Print some statistics
    total_nodes = len(predicate_only_names) + len(definitions)
    print("\nStatistics:")
    print(f"  Total LET definitions: {len(definitions)}")
    print(f"  Total unique predicate nodes: {len(predicate_only_names)}")
    print(f"  Total nodes in graph: {total_nodes}")
    print(f"  Total implications: {len(implications)}")
    if mode == "original":
        print(f"  LET definition edges: {edge_count}")
    if mode == "normal":
        print(f"  Total causality rules: {len(rules)}")
        print(f"  Causality edges: {causality_edge_count}")
    print(f"  Implication edges: {implication_edge_count}")
    if mode == "original" and len(definitions) > 0:
        print(f"  Average predicates per definition: {edge_count / len(definitions):.2f}")
    
    # Find most used predicates
    predicate_usage = {}
    for defn in definitions:
        for pred in defn["predicates"]:
            predicate_usage[pred] = predicate_usage.get(pred, 0) + 1
    
    if predicate_usage:
        most_used = sorted(predicate_usage.items(), key=lambda x: x[1], reverse=True)[:10]
        print("\nTop 10 most used predicates:")
        for pred, count in most_used:
            print(f"  {pred}: used in {count} definitions")
    
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate PyVis graph from MFOTL formula JSON')
    parser.add_argument('input', help='Input JSON file')
    parser.add_argument('output', help='Output HTML file')
    parser.add_argument('--normal', action='store_true', 
                       help='Process normal mode JSON (with CauByCau/CauBySup instead of LET definitions)')
    
    args = parser.parse_args()
    
    mode = "normal" if args.normal else "original"
    
    html_file = create_let_graph(args.input, args.output, mode=mode)
    
    # Open in browser
    abs_path = os.path.abspath(html_file)
    print(f"\nOpening {abs_path} in browser...")
    webbrowser.open('file://' + abs_path)
