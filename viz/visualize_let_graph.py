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


def create_let_graph(json_file, output_file):
    """Create PyVis graph from formula JSON showing LET definition dependencies."""
    
    # Load JSON
    with open(json_file, 'r') as f:
        formula = json.load(f)
    
    # Extract all LET definitions
    definitions = extract_let_definitions(formula)
    
    print(f"Found {len(definitions)} LET definitions")
    
    # Create network
    net = Network(height="900px", width="100%", directed=True, 
                  notebook=False, bgcolor="#ffffff", font_color="#333333")
    
    # Configure physics for better layout
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -15000,
          "centralGravity": 0.2,
          "springLength": 250,
          "springConstant": 0.02,
          "damping": 0.5,
          "avoidOverlap": 0.8
        },
        "stabilization": {
          "enabled": true,
          "iterations": 1000,
          "updateInterval": 25
        }
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
          "enabled": true,
          "color": "rgba(0,0,0,0.2)",
          "size": 10,
          "x": 3,
          "y": 3
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
          "type": "cubicBezier",
          "forceDirection": "none",
          "roundness": 0.5
        },
        "width": 1.5,
        "shadow": {
          "enabled": true,
          "color": "rgba(0,0,0,0.1)",
          "size": 5,
          "x": 2,
          "y": 2
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "hideEdgesOnDrag": false,
        "navigationButtons": true,
        "keyboard": {
          "enabled": true
        }
      }
    }
    """)
    
    # Collect all unique predicates across all definitions
    all_predicates = set()
    for defn in definitions:
        all_predicates.update(defn["predicates"])
    
    print(f"Found {len(all_predicates)} unique predicates")
    
    # Add predicate nodes (blue circles)
    for pred in all_predicates:
        net.add_node(pred, 
                    label=pred, 
                    color={"border": "#2980b9", "background": "#5dade2", "highlight": {"border": "#f39c12", "background": "#f1c40f"}},
                    shape="dot",
                    size=25,
                    font={"size": 14, "color": "#2c3e50"},
                    title=f"Predicate: {pred}")
    
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
            net.add_edge(let_id, pred, 
                        color={"color": "#bdc3c7", "highlight": "#e67e22", "opacity": 0.6},
                        width=2,
                        title=f"{defn['name']} uses {pred}")
            edge_count += 1
    
    print(f"Created {edge_count} edges")
    
    # Save the graph and add search functionality
    net.save_graph(output_file)
    
    # Prepare node list for dropdown
    all_nodes = sorted(list(all_predicates))
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
    print("\nStatistics:")
    print(f"  Total LET definitions: {len(definitions)}")
    print(f"  Total unique predicates: {len(all_predicates)}")
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
