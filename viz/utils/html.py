"""
Utilities for generating HTML components and templates.
"""

import os
import json
from jinja2 import Template
from .graph import format_scc_label


def create_edge_control(control_id, label, color, checked=True):
    """Create a single edge control HTML element."""
    checked_attr = ' checked' if checked else ''
    return (
        f'<label style="font-size: 12px;"><input type="checkbox" id="{control_id}"{checked_attr} />'
        f'<span class="edge-label"><span class="edge-indicator" style="background: {color};">'
        f'</span>{label}</span></label>'
    )


def build_edge_controls_html(has_definitions):
    """Build edge controls HTML for available edge types."""
    controls = []
    
    # LET/Definition edges
    if has_definitions:
        controls.append(create_edge_control("show-let-edges", "Definition Edges", "#bdc3c7"))
    
    # Monotonicity-based filtering
    controls.append('<div style="font-size: 11px; color: #555; margin-top: 10px; margin-bottom: 5px; font-weight: 600;">Filter by Monotonicity:</div>')
    controls.append(create_edge_control("show-monotonic-edges", "Monotonic Edges", "#27ae60"))
    controls.append(create_edge_control("show-antimonotonic-edges", "Antimonotonic Edges", "#e67e22"))
    controls.append(create_edge_control("show-neither-edges", "Neither Monotonicity Edges", "#9b59b6"))
    
    return '\n                '.join(controls)


def build_checkbox_items_html(node_ids, sccs=None, node_id_to_label=None):
    """Build checkbox items HTML for node selection.
    
    Args:
        node_ids: List of individual node IDs
        sccs: Optional list of SCCs (each SCC is a list of node IDs)
        node_id_to_label: Optional dict mapping node IDs to display labels
    """
    items = []
    
    # Add SCC groups first if provided
    if sccs:
        for i, scc in enumerate(sccs):
            display_name = format_scc_label(scc, strip_prefix=True)
            
            # Store the SCC nodes as a data attribute
            scc_nodes_json = json.dumps(sorted(scc))
            items.append(
                f'<div class="checkbox-item">\n'
                f'    <input type="checkbox" class="scc-checkbox" id="scc_{i}" data-scc-nodes=\'{scc_nodes_json}\' />\n'
                f'    <label for="scc_{i}" style="font-size: 12px; font-weight: 600; color: #f0ad4e;">{display_name}</label>\n'
                f'</div>'
            )
        
        # Add separator
        if items:
            items.append('<div style="border-top: 1px solid #ddd; margin: 8px 0;"></div>')
    
    # Add individual node checkboxes
    for node_id in node_ids:
        # Use display label if provided, otherwise format from node ID
        if node_id_to_label and node_id in node_id_to_label:
            display_name = node_id_to_label[node_id]
        else:
            # Fallback to simple formatting
            display_name = node_id
        
        items.append(
            f'<div class="checkbox-item">\n'
            f'    <input type="checkbox" id="{node_id}" value="{node_id}" />\n'
            f'    <label for="{node_id}" style="font-size: 12px;">{display_name}</label>\n'
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
                               scc_map_json, sccs_json, partitions_json, partition_labels_json,
                               partition_controls_html, stats_json, filter_polarity=False):
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
        partition_labels_json=partition_labels_json,
        stats_json=stats_json,
        filter_polarity=filter_polarity
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
