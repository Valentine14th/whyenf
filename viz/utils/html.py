"""
Utilities for generating HTML components and templates.
"""

import os
import json
from jinja2 import Template


def create_edge_control(control_id, label, color=None, checked=True):
    """Create a single edge control HTML element."""
    checked_attr = ' checked' if checked else ''
    indicator_style = f' style="background: {color};"' if color else ' class="implication"'
    return (
        f'<label style="font-size: 12px;"><input type="checkbox" id="{control_id}"{checked_attr} />'
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
            f'    <label for="node_{i}" style="font-size: 12px;">{name}</label>\n'
            f'</div>'
        )
    return '\n                '.join(items)


def build_partition_controls_html(partitions, partition_labels):
    """Build HTML for partition selection controls."""
    if not partitions:
        return ""
    
    items = []
    for i, partition_id in enumerate(sorted(partitions.keys(), key=int)):
        label = partition_labels.get(partition_id, f"Partition {partition_id}")
        items.append(
            f'<div class="checkbox-item">\n'
            f'    <input type="checkbox" id="partition_{i}" class="partition-checkbox" value="{partition_id}" />\n'
            f'    <label for="partition_{i}" style="font-size: 12px;">{label}</label>\n'
            f'</div>'
        )
    return '\n                    '.join(items)


def load_and_populate_template(template_file, edge_controls_html, checkbox_items_html, 
                               leaf_nodes_json, source_nodes_json,
                               scc_map_json, sccs_json, partitions_json, partition_labels_json, partition_controls_html):
    """Load HTML template and replace placeholders with generated content."""
    with open(template_file, 'r') as f:
        template_content = f.read()

    template = Template(template_content)
    
    widget_html = template.render(
        edge_controls=edge_controls_html,
        checkbox_items=checkbox_items_html,
        partition_controls=partition_controls_html,
        leaf_nodes_json=leaf_nodes_json,
        source_nodes_json=source_nodes_json,
        scc_map_json=scc_map_json,
        sccs_json=sccs_json,
        partitions_json=partitions_json,
        partition_labels_json=partition_labels_json
    )

    return widget_html


def inject_widget_into_graph_html(output_file, widget_html):
    """Read generated graph HTML and inject widget before closing body tag."""
    with open(output_file, 'r') as f:
        html_content = f.read()
    
    # Insert widget before closing body tag
    html_content = html_content.replace('</body>', widget_html + '</body>')
    
    with open(output_file, 'w') as f:
        f.write(html_content)
