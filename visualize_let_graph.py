#!/usr/bin/env python3
"""
Generate PyVis graph showing LET definition dependencies from MFOTL formula JSON.
Each predicate node is used only once and reused across different definitions.
"""

import json
import sys
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
    
    # Add custom search box HTML/JS
    with open(output_file, 'r') as f:
        html_content = f.read()
    
    # Insert search box HTML and JavaScript
    search_html = """
    <style>
        #search-container {
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            font-family: Arial, sans-serif;
            max-width: 400px;
        }
        #search-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        #search-label {
            font-weight: bold;
            color: #2c3e50;
            font-size: 13px;
        }
        #toggle-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: background-color 0.3s;
        }
        #toggle-btn:hover {
            background: #2980b9;
        }
        #search-content {
            display: block;
        }
        #search-content.hidden {
            display: none;
        }
        #search-input {
            width: 100%;
            padding: 8px;
            border: 2px solid #bdc3c7;
            border-radius: 4px;
            font-size: 14px;
            outline: none;
            margin-bottom: 10px;
            box-sizing: border-box;
        }
        #search-input:focus {
            border-color: #3498db;
        }
        #dropdown-list {
            max-height: 300px;
            overflow-y: auto;
            border: 2px solid #bdc3c7;
            border-radius: 4px;
            background: white;
            margin-bottom: 10px;
        }
        .checkbox-item {
            padding: 8px 12px;
            cursor: pointer;
            transition: background-color 0.2s;
            display: flex;
            align-items: center;
            border-bottom: 1px solid #ecf0f1;
        }
        .checkbox-item:hover {
            background-color: #ecf0f1;
        }
        .checkbox-item input[type="checkbox"] {
            margin-right: 8px;
            cursor: pointer;
        }
        .checkbox-item label {
            cursor: pointer;
            flex: 1;
            font-size: 13px;
            user-select: none;
        }
        #selected-nodes {
            margin-top: 10px;
            max-height: 100px;
            overflow-y: auto;
            padding: 5px;
            background: #ecf0f1;
            border-radius: 4px;
        }
        .selected-tag {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 4px 8px;
            margin: 3px;
            border-radius: 3px;
            font-size: 12px;
            cursor: pointer;
        }
        .selected-tag:hover {
            background: #2980b9;
        }
        .selected-tag::after {
            content: ' ×';
            margin-left: 5px;
            font-weight: bold;
        }
        #button-container {
            margin-top: 10px;
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        .btn-clear {
            background: #e74c3c;
            color: white;
            width: 100%;
        }
        .btn-clear:hover {
            background: #c0392b;
        }
        #search-results {
            margin-top: 8px;
            font-size: 12px;
            color: #7f8c8d;
        }
    </style>
    
    <div id="search-container">
        <div id="search-header">
            <span id="search-label">Select Events/Definitions</span>
            <button id="toggle-btn">Hide</button>
        </div>
        <div id="search-content">
            <input type="text" id="search-input" placeholder="Filter by name..." />
            <div id="dropdown-list">
""" + ''.join(f'''                <div class="checkbox-item">
                    <input type="checkbox" id="node_{i}" value="{name}" />
                    <label for="node_{i}">{name}</label>
                </div>
''' for i, name in enumerate(all_node_names)) + """
            </div>
            <div id="selected-nodes"></div>
            <div id="button-container">
                <button class="btn btn-clear" id="btn-clear">Clear All</button>
            </div>
            <div id="search-results"></div>
        </div>
    </div>
    
    <script type="text/javascript">
        document.addEventListener('DOMContentLoaded', function() {
            const searchInput = document.getElementById('search-input');
            const dropdownList = document.getElementById('dropdown-list');
            const selectedNodesDiv = document.getElementById('selected-nodes');
            const searchResults = document.getElementById('search-results');
            const btnClear = document.getElementById('btn-clear');
            const toggleBtn = document.getElementById('toggle-btn');
            const searchContent = document.getElementById('search-content');
            
            const checkboxItems = dropdownList.querySelectorAll('.checkbox-item');
            const checkboxes = dropdownList.querySelectorAll('input[type="checkbox"]');
            let selectedNodes = new Set();
            
            // Toggle visibility
            toggleBtn.addEventListener('click', function() {
                if (searchContent.classList.contains('hidden')) {
                    searchContent.classList.remove('hidden');
                    toggleBtn.textContent = 'Hide';
                } else {
                    searchContent.classList.add('hidden');
                    toggleBtn.textContent = 'Show';
                }
            });
            
            // Filter dropdown based on search
            searchInput.addEventListener('input', function() {
                const filter = this.value.toLowerCase();
                checkboxItems.forEach(item => {
                    const label = item.querySelector('label').textContent.toLowerCase();
                    item.style.display = label.includes(filter) ? 'flex' : 'none';
                });
            });
            
            // Update selected nodes display
            function updateSelectedDisplay() {
                selectedNodesDiv.innerHTML = '';
                if (selectedNodes.size === 0) {
                    selectedNodesDiv.innerHTML = '<div style="color: #95a5a6; font-size: 12px; padding: 5px;">No nodes selected</div>';
                    return;
                }
                
                selectedNodes.forEach(nodeName => {
                    const tag = document.createElement('span');
                    tag.className = 'selected-tag';
                    tag.textContent = nodeName;
                    tag.onclick = () => {
                        selectedNodes.delete(nodeName);
                        // Uncheck the checkbox
                        checkboxes.forEach(cb => {
                            if (cb.value === nodeName) cb.checked = false;
                        });
                        updateSelectedDisplay();
                        highlightNodes();
                    };
                    selectedNodesDiv.appendChild(tag);
                });
            }
            
            // Highlight selected nodes
            function highlightNodes() {
                if (selectedNodes.size === 0) {
                    network.selectNodes([]);
                    searchResults.textContent = '';
                    return;
                }
                
                // Find matching node IDs
                const allNodes = network.body.data.nodes.get();
                const matchingIds = [];
                
                selectedNodes.forEach(nodeName => {
                    const matches = allNodes.filter(node => 
                        node.label === nodeName || 
                        node.id === nodeName || 
                        node.id === 'LET_' + nodeName
                    );
                    matches.forEach(m => matchingIds.push(m.id));
                });
                
                if (matchingIds.length > 0) {
                    network.selectNodes(matchingIds);
                    
                    searchResults.textContent = `Highlighted ${matchingIds.length} node${matchingIds.length > 1 ? 's' : ''}`;
                    searchResults.style.color = '#27ae60';
                } else {
                    searchResults.textContent = 'No matching nodes found';
                    searchResults.style.color = '#e74c3c';
                }
            }
            
            // Handle checkbox changes
            checkboxes.forEach(checkbox => {
                checkbox.addEventListener('change', function() {
                    if (this.checked) {
                        selectedNodes.add(this.value);
                    } else {
                        selectedNodes.delete(this.value);
                    }
                    updateSelectedDisplay();
                    highlightNodes();
                });
            });
            
            // Make clicking on label/item also toggle checkbox
            checkboxItems.forEach(item => {
                item.addEventListener('click', function(e) {
                    if (e.target.tagName !== 'INPUT') {
                        const checkbox = this.querySelector('input[type="checkbox"]');
                        checkbox.checked = !checkbox.checked;
                        checkbox.dispatchEvent(new Event('change'));
                    }
                });
            });
            
            // Clear button
            btnClear.addEventListener('click', function() {
                selectedNodes.clear();
                checkboxes.forEach(cb => cb.checked = false);
                updateSelectedDisplay();
                network.selectNodes([]);
                searchResults.textContent = '';
                searchInput.value = '';
                checkboxItems.forEach(item => item.style.display = 'flex');
            });
            
            // Initialize display
            updateSelectedDisplay();
        });
    </script>
    """
    
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


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 visualize_let_graph.py <input.json> <output.html>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2]
    
    create_let_graph(json_file, output_file)
