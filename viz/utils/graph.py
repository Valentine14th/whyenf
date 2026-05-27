"""
Utilities for building and manipulating the graph structure.
"""

import networkx as nx
from .config import NODE_COLORS, EDGE_COLORS
from .merge import apply_merge_strategy


def format_rule_label(rule_label):
    if ':' in rule_label:
        # Split on the first colon to separate path from location info
        parts = rule_label.split('/', )
        file_path_with_location = parts[-1] if parts else rule_label
        return file_path_with_location
    return rule_label


def add_rule_nodes(net, expanded_rules) -> int:
    """Add rule nodes to the network.
    
    Args:
        net: PyVis network
        expanded_rules: List of expanded rule dicts with filter, effects, and provenance
    """
    node_count = 0
    for rule in expanded_rules:
        rule_id = rule['id']
        rule_type = rule.get('type', 'Unknown')
        rule_label = rule.get('label', rule_id)
        
        # Extract a short display name from the label
        display_label = format_rule_label(rule_label)
        
        # Create hover text with details including full label
        # Use provenance to show expanded names if available
        filter_display = []
        for pred in sorted(rule['filter']):
            provenance = rule['filter_provenance'].get(pred, pred)
            polarity = rule['events'].get(pred, {}).get('polarity', 'Unknown')
            filter_display.append(f"{provenance} ({polarity})")
        
        effects_display = []
        for pred in sorted(rule['effects']):
            provenance = rule['effects_provenance'].get(pred, pred)
            effect_type = rule['events'].get(pred, {}).get('effect', 'Unknown')
            effects_display.append(f"{provenance} ({effect_type})")
        
        hover_text = (
            f"Label: {rule_label}\n"
            f"Type: {rule_type}\n"
            f"Filter ({len(rule['filter'])} predicates):\n" +
            "\n".join(f"  • {p}" for p in filter_display) +
            f"\n\nEffects ({len(rule['effects'])} predicates):\n" +
            "\n".join(f"  • {p}" for p in effects_display)
        )
        
        # Color based on rule type
        color = NODE_COLORS["caubycau"] if rule_type == "CauByCau" else NODE_COLORS["caubysup"]
        
        net.add_node(
            rule_id,
            label=display_label,
            color=color,
            shape="box",
            size=35,
            font={"size": 14, "color": "#ffffff", "bold": True},
            shapeProperties={"borderRadius": 6},
            title=hover_text
        )
        node_count += 1
    
    return node_count

def _merge_polarity(pol1: str, pol2: str) -> str:
    """
    Combine two polarities when merging events with the same base name.
    
    Rules:
    - Monotonic + Monotonic = Monotonic
    - Antimonotonic + Antimonotonic = Antimonotonic
    - Monotonic + Antimonotonic = Neither
    - Anything + Neither = Neither
    - Anything + Irrelevant = Irrelevant
    """
    if pol1 == 'Irrelevant' or pol2 == 'Irrelevant':
        return 'Irrelevant'
    if pol1 == 'Neither' or pol2 == 'Neither':
        return 'Neither'
    if pol1 == pol2:
        return pol1
    # Monotonic + Antimonotonic = Neither
    return 'Neither'

def _expand_polarity(outer_polarity: str, inner_polarity: str) -> str:
    """
    Compose two polarities when expanding LETs into their consituent events.
    
    Rules:
    - Monotonic + Monotonic = Monotonic
    - Antimonotonic + Antimonotonic = Monotonic
    - Monotonic + Antimonotonic = Antimonotonic
    - Antimonotonic + Monotonic = Antimonotonic
    - Irrelevant + anything = Irrelevant
    - anything + Irrelevant = Irrelevant
    - Neither + anything = Neither (unless Irrelevant)
    - anything + Neither = Neither (unless Irrelevant)
    """
    if outer_polarity == 'Irrelevant' or inner_polarity == 'Irrelevant':
        return 'Irrelevant'
    if outer_polarity == 'Neither' or inner_polarity == 'Neither':
        return 'Neither'
    
    if outer_polarity == 'Monotonic':
        return inner_polarity
    elif outer_polarity == 'Antimonotonic':
        if inner_polarity == 'Monotonic':
            return 'Antimonotonic'
        elif inner_polarity == 'Antimonotonic':
            return 'Monotonic'
        else:
            return inner_polarity
    else:
        return inner_polarity
    
    
def expand_events(events: list, lets: dict, visited: set = None) -> tuple:
    """
    Expand events by recursively resolving let-bound predicates.
    
    For filters: recursively expand let-bound predicates to their constituent events,
                 composing polarities. Notation: e>e' means e' comes from let-bound event e.
    
    For effects: expand to effect events (as effects) and non-effect events (as filters).
    
    Args:
        events: list of event dicts with name, polarity, effect
        lets: dict of let bindings
        visited: set of already-visited let predicates (to avoid cycles)
        
    Returns:
        tuple: (expanded_effects, expanded_filters)
               where each is a list of (display_name, polarity, effect_type_or_none)
    """
    if visited is None:
        visited = set()
    
    expanded_effects = []
    expanded_filters = []
    
    for event in events:
        name = event['name']
        polarity = event.get('polarity', 'Monotonic')
        effect = event.get('effect') 
        
        # Check if this is a let-bound predicate
        if name in lets and name not in visited:
            let_data = lets[name]
            let_enftype = let_data['enftype']
            
            # Recursively expand the let binding's events
            new_visited = visited | {name}
            sub_expanded_effects, sub_expanded_filters = expand_events(
                let_data['events'], lets, new_visited
            )
            
            if effect in ('Sup', 'Cau'):
                # This is an effect on a let-bound predicate
                # The effect events from the let become effects here
                # The filter events from the let become filters here
                for sub_name, sub_pol, sub_eff in sub_expanded_effects:
                    display_name = f"{name}>{sub_name}"
                    composed_polarity = _expand_polarity(polarity, sub_pol)
                    # The effect type propagates from the outer effect
                    expanded_effects.append((display_name, composed_polarity, effect))
                
                for sub_name, sub_pol, _ in sub_expanded_filters:
                    display_name = f"{name}>{sub_name}"
                    composed_polarity = _expand_polarity(polarity, sub_pol)
                    # Skip Irrelevant filters
                    if composed_polarity != 'Irrelevant':
                        expanded_filters.append((display_name, composed_polarity, None))
            else:
                # This is a filter on a let-bound predicate
                # All events from the let become filters with composed polarity
                for sub_name, sub_pol, sub_eff in sub_expanded_effects:
                    display_name = f"{name}>{sub_name}"
                    composed_polarity = _expand_polarity(polarity, sub_pol)
                    # Skip Irrelevant filters
                    if composed_polarity != 'Irrelevant':
                        expanded_filters.append((display_name, composed_polarity, None))
                
                for sub_name, sub_pol, _ in sub_expanded_filters:
                    display_name = f"{name}>{sub_name}"
                    composed_polarity = _expand_polarity(polarity, sub_pol)
                    # Skip Irrelevant filters
                    if composed_polarity != 'Irrelevant':
                        expanded_filters.append((display_name, composed_polarity, None))
        else:
            # Only add if this is NOT a let-bound predicate
            # (If it's in lets but we're here, it means it was already visited - skip it)
            if name not in lets:
                if effect in ('Sup', 'Cau'):
                    expanded_effects.append((name, polarity, effect))
                else:
                    # Skip Irrelevant filters
                    if polarity != 'Irrelevant':
                        expanded_filters.append((name, polarity, None))
    
    return expanded_effects, expanded_filters

def merge_events_by_base(events: list, is_effect: bool = False) -> list:
    """
    Merge events that have the same base event name (rightmost part after '>').
    
    For each unique base event:
    - Collect all chains leading to it
    - Combine polarities: Monotonic + Antimonotonic = Neither
    - Keep the merged display name showing chains: "a>b, c>b" -> "b [via a, c]"
    
    Args:
        events: list of (display_name, polarity, effect_type_or_none)
        is_effect: whether these are effects (True) or filters (False)
        
    Returns:
        list of merged events: (display_name, base_name, combined_polarity, effect_type_or_none)
    """
    from collections import defaultdict
    
    # Group by base event name
    # For effects, also group by effect_type since Sup and Cau are different
    groups = defaultdict(list)
    
    for item in events:
        name, polarity, eff_type = item
        base_name = name.split('>')[-1]
        
        if is_effect:
            key = (base_name, eff_type)
        else:
            key = (base_name, None)
        
        groups[key].append((name, polarity, eff_type))
    
    # Merge each group
    merged = []
    for (base_name, eff_type), items in groups.items():
        # Build display name showing all chains (always use [via ...] format if chains exist)
        chains = []
        for name, _, _ in items:
            if '>' in name:
                # Extract the chain prefix (everything before the last >)
                chain = name.rsplit('>', 1)[0]
                chains.append(chain)
            # Skip direct events - they have no chain
        
        # Create display name with [via ...] format if chains exist
        if chains:
            chains_str = ', '.join(sorted(set(chains)))  # Deduplicate and sort chains
            display_name = f"{base_name} [via {chains_str}]"
        else:
            # All are direct events, no chain info needed
            display_name = base_name
        
        if len(items) == 1:
            # No merging needed for polarity
            _, polarity, effect_type = items[0]
            merged.append((display_name, base_name, polarity, effect_type))
        else:
            # Combine polarities
            combined_polarity = items[0][1]
            for _, pol, _ in items[1:]:
                combined_polarity = _merge_polarity(combined_polarity, pol)
            
            # Skip if combined polarity is Irrelevant (for filters)
            if not is_effect and combined_polarity == 'Irrelevant':
                continue
            
            merged.append((display_name, base_name, combined_polarity, eff_type))
    
    return merged


def expand_rules(rules, let_definitions_dict=None):
    """Expand rules by recursively resolving LET definitions.
    
    Args:
        rules: List of rule dictionaries with 'id', 'label', 'events' fields
        let_definitions_dict: Dict mapping LET names to their definitions (optional)
    
    Returns:
        List of expanded rule dictionaries with fields:
        - id, label: original rule identifiers
        - filter, effects: sets of base predicate names
        - filter_provenance, effects_provenance: dicts mapping base name to display name
        - events: dict mapping base name to {polarity, effect}
    """
    expanded_rules = []
    for rule in rules:
        # Expand LET definitions in effects and filters, composing polarities
        expanded_effect, expanded_filter = expand_events(
            rule['events'], 
            let_definitions_dict or {}, 
            set()  # Initialize as empty set, not list
        )
        
        # Merge events by base name, combining polarities
        merged_effect = merge_events_by_base(expanded_effect, is_effect=True)
        merged_filter = merge_events_by_base(expanded_filter, is_effect=False)
        
        # Extract base names, provenance, and events from tuples
        effects_set = set()
        effects_provenance = {}
        filter_set = set()
        filter_provenance = {}
        events_dict = {}
        
        for display_name, base_name, polarity, effect_type in merged_effect:
            effects_set.add(base_name)
            effects_provenance[base_name] = display_name
            events_dict[base_name] = {'polarity': polarity, 'effect': effect_type}
        
        for display_name, base_name, polarity, effect_type in merged_filter:
            filter_set.add(base_name)
            filter_provenance[base_name] = display_name
            
            # If predicate appears in both effects and filters
            if base_name in events_dict:
                # Keep the effect type from the effect entry, but update polarity from filter
                events_dict[base_name]['polarity'] = polarity
            else:
                events_dict[base_name] = {'polarity': polarity, 'effect': effect_type}
        
        expanded_rules.append({
            'id': rule['id'],
            'label': rule.get('label', rule['id']),
            'type': rule.get('type', 'Unknown'),
            'filter': filter_set,
            'effects': effects_set,
            'filter_provenance': filter_provenance,
            'effects_provenance': effects_provenance,
            'events': events_dict,
        })
    
    return expanded_rules


def add_rule_edges(net, expanded_rules):
    """Add edges between rules where one rule's effects appear in another's filter.
    
    Args:
        net: PyVis network
        expanded_rules: List of expanded rule dicts (output from expand_rules function)
    
    Edge color is determined by the monotonicity of shared predicates in the target rule's filter:
    - Green: All shared predicates are Monotonic
    - Orange: All shared predicates are Antimonotonic  
    - Purple: Neither monotonicity
    """
    # Simple shared predicate analysis
    edge_count = 0
    stats = {
        'monotonic': 0,
        'antimonotonic': 0,
        'neither': 0
    }
    
    for rule_from in expanded_rules:
        for rule_to in expanded_rules:
            if rule_from['id'] == rule_to['id']:
                continue
            
            # Check if any of rule_from's effects appear in rule_to's filter
            common_predicates = rule_from['effects'] & rule_to['filter']
            
            if common_predicates:
                # Determine monotonicity
                monotonicities = set()
                monotonicity_details = []
                
                # Check the combined polarity of each shared predicate in the target rule's events
                for pred in common_predicates:
                    polarity = rule_to['events'].get(pred, {}).get('polarity', 'Neither')
                    monotonicities.add(polarity)
                    monotonicity_details.append(f"{pred} ({polarity})")
                
                # Determine edge color based on monotonicity
                if monotonicities == {'Monotonic'}:
                    edge_color = EDGE_COLORS["monotonic"]
                    monotonicity_type = "monotonic"
                    stats['monotonic'] += 1
                elif monotonicities == {'Antimonotonic'}:
                    edge_color = EDGE_COLORS["antimonotonic"]
                    monotonicity_type = "antimonotonic"
                    stats['antimonotonic'] += 1
                else:
                    edge_color = EDGE_COLORS["neither"]
                    monotonicity_type = "neither"
                    stats['neither'] += 1
                
                # Create edge title with LET provenance
                rule_from_label = rule_from.get('label', rule_from['id']).split('/')[-1]
                rule_to_label = rule_to.get('label', rule_to['id']).split('/')[-1]
                
                pred_str = ", ".join(sorted(common_predicates))
                
                # Build detailed predicate info with LET provenance
                predicate_details = []
                for pred in sorted(common_predicates):
                    polarity = rule_to['events'].get(pred, {}).get('polarity', 'Neither')
                    
                    # Get LET provenance for source (effects) and target (filter)
                    from_display = rule_from['effects_provenance'].get(pred, pred)
                    to_display = rule_to['filter_provenance'].get(pred, pred)
                    
                    detail_parts = [f"{pred} ({polarity})"]
                    
                    # Show provenance if display name differs from base name
                    if from_display != pred or to_display != pred:
                        provenance_parts = []
                        if from_display != pred:
                            provenance_parts.append(f"from: {from_display}")
                        if to_display != pred:
                            provenance_parts.append(f"to: {to_display}")
                        detail_parts.append(f"[{'; '.join(provenance_parts)}]")
                    
                    predicate_details.append(" ".join(detail_parts))
                
                title = (
                    f"{rule_from_label} → {rule_to_label}\n" +
                    f"{rule_from.get('type', 'Unknown')} -> {monotonicity_type.capitalize()}\n " +
                    f"Shared predicates ({len(common_predicates)}):\n" +
                    "\n".join(f"  • {detail}" for detail in predicate_details)
                )
                
                # Create edge
                net.add_edge(
                    rule_from['id'],
                    rule_to['id'],
                    color={"color": edge_color, "highlight": "#e74c3c", "opacity": 0.7},
                    width=2,
                    title=title,
                    label=str(len(common_predicates)),
                    monotonicity_type=monotonicity_type
                )
                edge_count += 1
    
    # Print statistics
    _print_edge_statistics(edge_count, stats)
    shared_predicate_count = _compute_shared_predicates(net.edges)
    _print_shared_predicates(shared_predicate_count)
    
    return edge_count


def filter_polarity_edges(net, expanded_rules):
    """Remove polarity edges from the graph.
    
    Removes edges where:
    - Source node is CauBySup AND edge is monotonic, OR
    - Source node is CauByCau AND edge is antimonotonic
    
    These are edges where a rule causally depends on predicates with the opposite
    monotonicity type (polarity causality).
    
    Args:
        net: PyVis network with edges to filter
        expanded_rules: List of expanded rule dicts with 'id' and 'type' fields
    
    Returns:
        Number of edges removed
    """
    # Build mapping of rule ID to rule type
    rule_type_map = {rule['id']: rule.get('type', 'Unknown') for rule in expanded_rules}
    
    # Find edges to remove
    edges_to_remove = []
    for i, edge in enumerate(net.edges):
        source_id = edge['from']
        monotonicity_type = edge.get('monotonicity_type', '')
        
        # Get source node type
        source_type = rule_type_map.get(source_id)
        
        # Check if edge should be removed
        if (source_type == 'CauBySup' and monotonicity_type == 'monotonic') or \
           (source_type == 'CauByCau' and monotonicity_type == 'antimonotonic'):
            edges_to_remove.append(i)
    
    # Remove edges in reverse order to maintain indices
    removed_count = len(edges_to_remove)
    for idx in reversed(edges_to_remove):
        net.edges.pop(idx)
    
    if removed_count > 0:
        print(f"\nFiltered {removed_count} polarity edges:")
        print(f"  - CauByCau with antimonotonic edges")
        print(f"  - CauBySup with monotonic edges")
        
        # Count remaining edges by monotonicity
        remaining_stats = {
            'monotonic': 0,
            'antimonotonic': 0,
            'neither': 0
        }
        for edge in net.edges:
            monotonicity_type = edge.get('monotonicity_type', '')
            if monotonicity_type in remaining_stats:
                remaining_stats[monotonicity_type] += 1
        
        remaining_total = sum(remaining_stats.values())
        print(f"\nRemaining edges after filtering: {remaining_total}")
        if remaining_total > 0:
            print(f"  By monotonicity:")
            print(f"    - Monotonic: {remaining_stats['monotonic']} ({100*remaining_stats['monotonic']/remaining_total:.1f}%)")
            print(f"    - Antimonotonic: {remaining_stats['antimonotonic']} ({100*remaining_stats['antimonotonic']/remaining_total:.1f}%)")
            print(f"    - Neither: {remaining_stats['neither']} ({100*remaining_stats['neither']/remaining_total:.1f}%)")
        
        # Compute and print shared predicates after filtering
        shared_after = _compute_shared_predicates(net.edges)
        _print_shared_predicates(shared_after, " (after polarity filtering)")
    
    return removed_count


def format_scc_label(scc_nodes, strip_prefix=False, node_labels=None):
    """Format SCC label showing nodes.
    
    Args:
        scc_nodes: List of node IDs in the SCC
        strip_prefix: If True, remove RULE_ prefix from node names
        node_labels: Optional dict mapping node IDs to display labels
    
    Returns:
        Formatted string
    """
    sorted_nodes = sorted(scc_nodes)
    
    # Use node labels if provided, otherwise use node IDs
    if node_labels:
        # Format labels 
        display_nodes = [format_rule_label(node_labels.get(n, n)) for n in sorted_nodes]
    elif strip_prefix:
        display_nodes = [n.replace('RULE_', '') for n in sorted_nodes]
    else:
        display_nodes = sorted_nodes
    
    if len(sorted_nodes) <= 3:
        node_list = ", ".join(display_nodes)
        return f"SCC [{node_list}]"
    else:
        node_preview = ", ".join(display_nodes[:3])
        return f"SCC [{node_preview}, ... {len(sorted_nodes)} nodes]"


def _build_graph_and_compute_sccs(net):
    """Build networkx graph and compute all SCCs.
    
    Returns:
        - nx_graph: NetworkX DiGraph
        - sccs_lists: List of all SCCs (list of node lists)
        - node_to_scc_map: Dict mapping node_id to SCC index
        - condensed: Condensed graph (DAG of SCCs)
    """
    # Build networkx graph
    nx_graph = nx.DiGraph()
    for node in net.nodes:
        nx_graph.add_node(node['id'])
    for edge in net.edges:
        nx_graph.add_edge(edge['from'], edge['to'])
    
    # Find all SCCs
    sccs_lists = list(nx.strongly_connected_components(nx_graph))
    sccs_lists = [list(scc) for scc in sccs_lists]
    
    # Create condensed graph (DAG of SCCs)
    condensed_nx_graph = nx.condensation(nx_graph)
    
    return sccs_lists, condensed_nx_graph


def _merge_partitions(partitions, partition_labels, sccs_all):
    """Merge partitions with identical node sets.
    
    Excludes anchor nodes before comparing (merge if same descendants).
    
    Args:
        partitions: Dict mapping anchor SCC index to set of node IDs
        partition_labels: Dict mapping anchor SCC index to label
        sccs_all: List of all SCCs
    
    Returns:
        - merged_partitions: Dict of merged partitions
        - merged_labels: Dict of merged labels
        - node_set_to_anchors: Dict mapping node sets to anchor indices (for statistics)
    """
    # Group partitions by their node sets
    node_set_to_anchors = {}
    for anchor_idx, nodes in partitions.items():
        # Exclude anchor nodes from comparison
        anchor_scc_nodes = set(sccs_all[anchor_idx])
        comparison_nodes = nodes - anchor_scc_nodes
        
        frozen_nodes = frozenset(comparison_nodes)
        
        if frozen_nodes not in node_set_to_anchors:
            node_set_to_anchors[frozen_nodes] = []
        node_set_to_anchors[frozen_nodes].append(anchor_idx)
    
    # Create merged partitions and labels
    merged_partitions = {}
    merged_labels = {}
    for frozen_nodes, anchor_indices in node_set_to_anchors.items():
        # Skip partitions with 0 non-leaf nodes
        if len(frozen_nodes) == 0:
            continue
            
        # Use the first anchor index as the key for the merged partition
        key_idx = anchor_indices[0]
        # Include all anchor nodes from all merged partitions
        all_nodes = set(frozen_nodes)
        for idx in anchor_indices:
            all_nodes.update(sccs_all[idx])
        merged_partitions[key_idx] = all_nodes
        
        # Create label combining all anchor names with node count
        anchor_names = sorted([partition_labels[idx] for idx in anchor_indices])
        if len(anchor_names) == 1:
            label_base = anchor_names[0]
        else:
            label_base = f"{', '.join(anchor_names[:-1])} & {anchor_names[-1]}"
        
        # Generate label with leaf suffix
        suffix = f"leaf{'ves' if len(anchor_names) > 1 else ''}"
        merged_labels[key_idx] = f"{label_base} ({len(all_nodes) - len(anchor_names)} nodes, {len(anchor_names)} {suffix})"
    
    return merged_partitions, merged_labels


def _print_partition_statistics(sccs_all, sccs_nontrivial, anchor_sccs, partitions, merged_partitions, partition_type):
    """Print partition computation statistics.
    
    Args:
        sccs_all: List of all SCCs
        sccs_nontrivial: List of non-trivial SCCs (size > 1)
        anchor_sccs: List of anchor SCC indices (sources or leaves)
        partitions: Dict of initial partitions before merging
        merged_partitions: Dict of partitions after merging
        partition_type: "source" or "leaf" for display purposes
    """
    print(f"\nPartition Statistics ({partition_type}-based):")
    print(f"Found {len(sccs_all)} SCCs (including trivial ones)")
    print(f"Filtered to {len(sccs_nontrivial)} non-trivial SCCs (size > 1)")
    print(f"Found {len(anchor_sccs)} leaf SCCs in condensed graph")
    print(f"Computed {len(partitions)} initial {partition_type}-based partitions")
    print(f"Merged into {len(merged_partitions)} unique partitions\n")


def _print_common_nodes(partitions, partition_labels, node_labels=None):
    """Print nodes that are common to all partitions.
    
    Args:
        partitions: Dict mapping partition index to set of node IDs
        partition_labels: Dict mapping partition index to label string
        node_labels: Optional dict mapping node IDs to display labels
    """
    if not partitions:
        print("No partitions to analyze for common nodes.")
        return
    
    if len(partitions) == 1:
        print("Only one partition exists - all nodes are 'common' to that partition.")
        return
    
    # Compute intersection of all partitions
    partition_list = list(partitions.values())
    common_nodes = set(partition_list[0])
    
    for partition_nodes in partition_list[1:]:
        common_nodes &= partition_nodes
    
    # Print results
    print(f"Nodes common to all {len(partitions)} partitions: {len(common_nodes)}")
    
    if common_nodes:     
        # Print in columns for better readability
        print("  Common nodes:")
        for i in range(0, len(common_nodes), 5):
            batch = list(common_nodes)[i:i+5]
            # Use node labels if available, otherwise use node IDs
            if node_labels:
                display_batch = [node_labels.get(node_id, node_id) for node_id in batch]
            else:
                display_batch = batch
            print("    " + ", ".join(display_batch))
        print()
    else:
        print("  No nodes are common to all partitions.\n")

def compute_backward_partitions(
    net,
    node_labels,
    merge_strategy='by_descendants',
    max_merge_size=None,
    merge_single_rule_components=True,
):
    """
    Compute backward-reachable partitions from leaves (NOT successor-closed).
    
    Each partition includes only nodes that can reach a leaf node (node with no outgoing 
    edges). Also marks nodes in leaf/source SCCs.
    
    Args:
        net: PyVis network
        node_labels: Dict mapping node IDs to display labels
        merge_strategy: Name of the merging strategy to use (default: 'by_descendants')
                       Available: 'by_descendants', 'no_merge'
        max_merge_size: Maximum number of partitions to merge together (None for unlimited)
        merge_single_rule_components: Whether one-rule components are mergeable under
            merge strategies that combine compatible partitions.
    
    Returns:
        - sccs_nontrivial: List of non-trivial SCCs (size > 1) 
        - node_to_scc_map: Dict mapping node_id to SCC index in sccs_nontrivial
        - partitions: Dict mapping leaf SCC index to set of backward-reachable node IDs
        - partition_labels: Dict mapping leaf SCC index to leaf node name
        - stats: Dict with partition statistics
        - leaf_nodes: Set of all nodes in leaf SCCs
        - source_nodes: Set of all nodes in source SCCs
    """

    sccs_lists, condensed_nx_graph = _build_graph_and_compute_sccs(net)
    
    # Find leaf and source SCCs in condensed graph
    leaf_sccs = [node for node in condensed_nx_graph.nodes() if condensed_nx_graph.out_degree(node) == 0]
    source_sccs = [node for node in condensed_nx_graph.nodes() if condensed_nx_graph.in_degree(node) == 0]
    
    # For each leaf SCC, compute backward-reachable set 
    partitions = {}
    partition_labels = {}
    for leaf_scc_idx in leaf_sccs:
        # Get all SCCs that can reach this leaf SCC (predecessors/ancestors in DAG)
        backward_reachable_sccs = nx.ancestors(condensed_nx_graph, leaf_scc_idx)
        backward_reachable_sccs.add(leaf_scc_idx)  # Include the leaf itself
        
        # Expand to original nodes 
        partition_nodes = set()
        for scc_idx in backward_reachable_sccs:
            partition_nodes.update(sccs_lists[scc_idx])
        
        partitions[leaf_scc_idx] = partition_nodes
        # Label the partition using the leaf SCC's nodes (anchor nodes)
        anchor_scc_nodes = sccs_lists[leaf_scc_idx]
        if len(anchor_scc_nodes) <= 1:
            node_id = sorted(anchor_scc_nodes)[0]
            partition_labels[leaf_scc_idx] = node_labels.get(node_id, node_id)
        else:
            partition_labels[leaf_scc_idx] = format_scc_label(anchor_scc_nodes, node_labels=node_labels)
    
    # Merge partitions with specified strategy
    merged_partitions, merged_labels, strategy_name = apply_merge_strategy(
        partitions,
        partition_labels,
        sccs_lists,
        strategy=merge_strategy,
        max_merge_size=max_merge_size,
        merge_single_rule_components=merge_single_rule_components,
    )
    
    # Filter SCCs to only non-trivial ones (size > 1) 
    sccs_nontrivial = [scc for scc in sccs_lists if len(scc) > 1]
    node_to_scc_map = {node_id: idx for idx, scc in enumerate(sccs_nontrivial) for node_id in scc}
    
    _print_partition_statistics(sccs_lists, sccs_nontrivial, leaf_sccs, partitions, merged_partitions, "backward")
    
    # Compute and print common nodes across all partitions
    _print_common_nodes(merged_partitions, merged_labels, node_labels)
    
    stats = {
        'initial_count': len(partitions),
        'merged_count': len(merged_partitions),
        'strategy': strategy_name,
        'max_merge_size': max_merge_size,
        'merge_single_rule_components': merge_single_rule_components,
    }
    
    # Mark nodes in leaf/source SCCs
    leaf_nodes, source_nodes = mark_source_and_leaf_scc_nodes(net, sccs_lists, leaf_sccs, source_sccs, node_labels)
    
    return sccs_nontrivial, node_to_scc_map, merged_partitions, merged_labels, stats, leaf_nodes, source_nodes


def mark_source_and_leaf_scc_nodes(net, sccs_lists, leaf_sccs, source_sccs, node_labels):
    """Mark all nodes in leaf/source SCCs with clear labels.
    
    Args:
        net: PyVis network
        sccs_lists: List of all SCCs (each SCC is a list of node IDs)
        leaf_sccs: List of leaf SCC indices in condensed graph
        source_sccs: List of source SCC indices in condensed graph
        node_labels: Dict mapping node IDs to labels
    
    Returns:
        Tuple of (leaf_nodes_set, source_nodes_set) containing all nodes in leaf/source SCCs
    """
    # Collect all nodes in leaf and source SCCs
    leaf_nodes = set()
    source_nodes = set()
    
    for scc_idx in leaf_sccs:
        leaf_nodes.update(sccs_lists[scc_idx])
    
    for scc_idx in source_sccs:
        source_nodes.update(sccs_lists[scc_idx])
    
    # Update node labels and titles
    for node in net.nodes:
        node_id = node['id']
        current_label = node.get('label', node_id)
        
        if node_id in leaf_nodes:
            node['title'] = node.get('title', '') + '\n[IN LEAF SCC - SCC has no outgoing edges]'
        elif node_id in source_nodes:
            node['title'] = node.get('title', '') + '\n[IN SOURCE SCC - SCC has no incoming edges]'
    
    return leaf_nodes, source_nodes


def _compute_shared_predicates(edges):
    """Compute how often each predicate is shared across edges.
    
    Args:
        edges: List of edge dictionaries with 'title' field containing predicate info
    
    Returns:
        Dictionary mapping predicate name to count of edges it appears in
    """
    shared_predicate_count = {}
    
    for edge in edges:
        title = edge.get('title', '')
        # Extract predicates from title line "Shared predicates: pred1, pred2, ..."
        if 'Shared predicates:' in title:
            lines = title.split('\n')
            for line in lines:
                if line.startswith('Shared predicates:'):
                    pred_str = line.replace('Shared predicates:', '').strip()
                    predicates = [p.strip() for p in pred_str.split(',')]
                    for pred in predicates:
                        if pred:
                            shared_predicate_count[pred] = shared_predicate_count.get(pred, 0) + 1
    
    return shared_predicate_count

def print_graph_statistics(definitions, predicate_only_names, edge_count, 
                          implications, implication_edge_count, rules=None, 
                          causality_edge_count=0):
    """Print comprehensive statistics about the graph."""
    total_nodes = len(predicate_only_names) + len(definitions)
    print(f"\nGraph Statistics:")
    print(f"  Nodes:")
    print(f"    - LET definitions: {len(definitions)}")
    print(f"    - Unique predicates: {len(predicate_only_names)}")
    print(f"    - Total nodes: {total_nodes}")
    print(f"  Edges:")
    if rules:
        print(f"    - Causality rules: {len(rules)}")
        print(f"    - Causality edges: {causality_edge_count}")
    if definitions:
        print(f"    - LET definition edges: {edge_count}")
        if edge_count > 0:
            print(f"    - Average predicates per LET definition: {edge_count / len(definitions):.2f}")
    print(f"    - Implications: {len(implications)}")
    print(f"    - Implication edges: {implication_edge_count}")
    
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



def _print_shared_predicates(shared_predicate_count, label=""):
    """Print top 10 most shared predicates.
    
    Args:
        shared_predicate_count: Dict mapping predicate name to count
        label: Optional label to distinguish different printouts
    """
    if shared_predicate_count:
        top_shared = sorted(shared_predicate_count.items(), key=lambda x: x[1], reverse=True)[:10]
        print(f"\n  Top 10 most shared predicates{label}:")
        for pred, count in top_shared:
            print(f"    - {pred}: shared in {count} edge{'s' if count > 1 else ''}")


def _print_edge_statistics(edge_count, stats):
    """Print edge statistics including monotonicity breakdown.
    
    Args:
        edge_count: Total number of edges
        stats: Dictionary with keys 'monotonic', 'antimonotonic', 'neither' and their respective counts
    """
    print(f"\nEdge Statistics:")
    print(f"  Total edges: {edge_count}")
    
    if edge_count > 0:
        print(f"  By monotonicity:")
        print(f"    - Monotonic: {stats['monotonic']} ({100*stats['monotonic']/edge_count:.1f}%)")
        print(f"    - Antimonotonic: {stats['antimonotonic']} ({100*stats['antimonotonic']/edge_count:.1f}%)")
        print(f"    - Neither: {stats['neither']} ({100*stats['neither']/edge_count:.1f}%)")
    else:
        print(f"  By monotonicity:")
        print(f"    - Monotonic: 0")
        print(f"    - Antimonotonic: 0")
        print(f"    - Neither: 0")
