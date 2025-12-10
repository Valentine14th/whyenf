#!/usr/bin/env python3
"""
Generate PyVis graph showing LET definition dependencies from MFOTL formula JSON.
Each predicate node is used only once and reused across different definitions.
"""

import json
import sys
import os
import webbrowser
from pyvis.network import Network


def extract_predicates(node, predicates_set):
    """Recursively extract all predicate names from a formula node."""
    if not isinstance(node, dict):
        return
    
    if node.get("constructor") == "Predicate":
        predicates_set.add(node["name"])
        return
    
    # Recurse through common formula structures
    if "formula" in node:
        extract_predicates(node["formula"], predicates_set)
    if "body" in node:
        extract_predicates(node["body"], predicates_set)
    if "arg" in node:  # For Neg, Prev, Next, etc.
        extract_predicates(node["arg"], predicates_set)
    if "args" in node and isinstance(node["args"], list):
        for arg in node["args"]:
            extract_predicates(arg, predicates_set)
    if "left" in node:
        extract_predicates(node["left"], predicates_set)
    if "right" in node:
        extract_predicates(node["right"], predicates_set)
    if "in" in node:
        extract_predicates(node["in"], predicates_set)


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


def create_let_graph(json_file, output_file):
    """Create PyVis graph from formula JSON showing LET definition dependencies."""
    
    # Load JSON
    with open(json_file, 'r') as f:
        formula = json.load(f)
    
    # Extract all LET definitions
    definitions = extract_let_definitions(formula)
    
    print(f"Found {len(definitions)} LET definitions")
    
    # Extract all implications
    implications = extract_implications(formula)
    
    print(f"Found {len(implications)} implications")
    
    # Create network
    net = Network(height="900px", width="100%", directed=True, 
                  notebook=False, bgcolor="#ffffff", font_color="#333333")
    
    # Configure physics for better layout and performance
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.6,
          "avoidOverlap": 0.5
        },
        "stabilization": {
          "enabled": true,
          "iterations": 500,
          "updateInterval": 50
        },
        "maxVelocity": 50,
        "minVelocity": 0.75,
        "solver": "barnesHut",
        "timestep": 0.5
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
        }
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
    
    # Collect all unique predicates from LET definitions
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
    
    # Only create predicate nodes for names that are NOT LET definitions
    predicate_only_names = (let_predicates | implication_predicates) - let_definition_names
    
    print(f"Found {len(let_predicates)} predicates in LET definitions")
    print(f"Found {len(implication_predicates)} predicates in implications")
    print(f"Found {len(let_definition_names)} LET definitions")
    print(f"Found {len(predicate_only_names)} unique predicate nodes (excluding LET definition names)")
    
    # Add predicate nodes (blue circles) - only for names that aren't LET definitions
    for pred in predicate_only_names:
        in_lets = pred in let_predicates
        in_implications = pred in implication_predicates
        
        # Build title based on where predicate appears
        title_parts = [f"Predicate: {pred}"]
        if in_lets and in_implications:
            title_parts.append("(Used in LET definitions and implications)")
        elif in_lets:
            title_parts.append("(Used in LET definitions)")
        elif in_implications:
            title_parts.append("(Used only in implications)")
        
        net.add_node(pred, 
                    label=pred, 
                    color={"border": "#2980b9", "background": "#5dade2", "highlight": {"border": "#f39c12", "background": "#f1c40f"}},
                    shape="dot",
                    size=25,
                    font={"size": 14, "color": "#2c3e50"},
                    title="\n".join(title_parts))
    
    # Add LET definition nodes (red boxes)
    for defn in definitions:
        let_id = f"LET_{defn['name']}"
        label = f"{defn['name']}"
        if defn['type']:
            label += f"\n({defn['type']})"
        
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
                <label>
                    <input type="checkbox" id="show-let-edges" checked />
                    <span class="edge-label">
                        <span class="edge-indicator let"></span>
                        LET Definition Edges
                    </span>
                </label>
                <label>
                    <input type="checkbox" id="show-implication-edges" checked />
                    <span class="edge-label">
                        <span class="edge-indicator implication"></span>
                        Implication Edges
                    </span>
                </label>
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
    print(f"  LET definition edges: {edge_count}")
    print(f"  Implication edges: {implication_edge_count}")
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
    if len(sys.argv) != 3:
        print("Usage: python3 visualize_let_graph.py <input.json> <output.html>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2]
    
    html_file = create_let_graph(json_file, output_file)
    
    # Open in browser
    abs_path = os.path.abspath(html_file)
    print(f"\nOpening {abs_path} in browser...")
    webbrowser.open('file://' + abs_path)
