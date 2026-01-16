"""
Configuration constants for graph visualization.
"""

# Physics configuration for the network
PHYSICS_OPTIONS = {
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

# Node color schemes
NODE_COLORS = {
    "predicate": {
        "border": "#2980b9",
        "background": "#5dade2",
        "highlight": {"border": "#f39c12", "background": "#f1c40f"}
    },
    "let": {
        "border": "#c0392b",
        "background": "#ec7063",
        "highlight": {"border": "#d68910", "background": "#f39c12"}
    },
    "caubycau": {
        "border": "#16a085",
        "background": "#1abc9c",
        "highlight": {"border": "#d68910", "background": "#f39c12"}
    },
    "caubysup": {
        "border": "#8e44ad",
        "background": "#9b59b6",
        "highlight": {"border": "#d68910", "background": "#f39c12"}
    },
    "leaf_let": {
        "border": "#943126",
        "background": "#cd6155",
        "highlight": {"border": "#d68910", "background": "#f39c12"}
    },
    "leaf_pred": {
        "border": "#5d6d7e",
        "background": "#85929e",
        "highlight": {"border": "#f39c12", "background": "#f1c40f"}
    },
    "source_let": {
        "border": "#d68910",
        "background": "#f39c12",
        "highlight": {"border": "#d68910", "background": "#f39c12"}
    },
    "source_pred": {
        "border": "#7d3c98",
        "background": "#af7ac5",
        "highlight": {"border": "#f39c12", "background": "#f1c40f"}
    }
}

# Edge colors
EDGE_COLORS = {
    "let": "#bdc3c7",
    "implication": "#9b59b6",
    "caubycau": "#27ae60",
    "caubysup": "#3498db",
    "mixed": "#9b59b6"
}
