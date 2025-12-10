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
                  notebook=False, bgcolor="#222222", font_color="white")
    
    # Configure physics for better layout
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04
        }
      },
      "nodes": {
        "font": {
          "size": 14
        }
      },
      "edges": {
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 0.5
          }
        },
        "smooth": {
          "type": "continuous"
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
                    color="#3498db",
                    shape="ellipse",
                    size=20,
                    title=f"Predicate: {pred}")
    
    # Add LET definition nodes (red boxes)
    for defn in definitions:
        let_id = f"LET_{defn['name']}"
        label = f"{defn['name']}"
        if defn['type']:
            label += f"\n({defn['type']})"
        
        net.add_node(let_id,
                    label=label,
                    color="#e74c3c",
                    shape="box",
                    size=25,
                    title=f"LET definition: {defn['name']}\nType: {defn['type']}\nUses {len(defn['predicates'])} predicates")
    
    # Add edges from LET definitions to their predicates
    edge_count = 0
    for defn in definitions:
        let_id = f"LET_{defn['name']}"
        for pred in defn["predicates"]:
            net.add_edge(let_id, pred, 
                        color="#95a5a6",
                        title=f"{defn['name']} uses {pred}")
            edge_count += 1
    
    print(f"Created {edge_count} edges")
    
    # Save the graph
    net.save_graph(output_file)
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
