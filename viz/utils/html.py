"""
Utilities for generating HTML components and templates.
"""

import os
import json


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


def load_and_populate_template(template_file, edge_controls_html, checkbox_items_html, 
                               leaf_nodes_json, source_nodes_json):
    """Load HTML template and replace placeholders with generated content."""
    with open(template_file, 'r') as f:
        widget_template = f.read()
    
    # Replace placeholders in template
    widget_html = (widget_template
                   .replace('<!-- EDGE_CONTROLS_PLACEHOLDER -->', edge_controls_html)
                   .replace('<!-- CHECKBOX_ITEMS_PLACEHOLDER -->', checkbox_items_html)
                   .replace('<!-- LEAF_NODES_JSON -->', leaf_nodes_json)
                   .replace('<!-- SOURCE_NODES_JSON -->', source_nodes_json))
    
    return widget_html


def inject_widget_into_graph_html(output_file, widget_html):
    """Read generated graph HTML and inject widget before closing body tag."""
    with open(output_file, 'r') as f:
        html_content = f.read()
    
    # Insert widget before closing body tag
    html_content = html_content.replace('</body>', widget_html + '</body>')
    
    with open(output_file, 'w') as f:
        f.write(html_content)
