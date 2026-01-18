"""
Functions for extracting data from MFOTL formula JSON.
"""


def extract_predicates(node, predicates_set=None):
    """Recursively extract all predicate names from a formula node."""
    if predicates_set is None:
        predicates_set = set()
    
    if isinstance(node, list):
        for item in node:
            extract_predicates(item, predicates_set)
        return predicates_set
    
    if not isinstance(node, dict):
        return predicates_set
    
    # Check if this is a Predicate constructor (with or without apostrophe)
    constructor = node.get("constructor")
    if constructor in ["Predicate", "Predicate'"]:
        predicates_set.add(node["name"])
    
    # Recursively traverse all values in the dictionary
    for value in node.values():
        if isinstance(value, (dict, list)):
            extract_predicates(value, predicates_set)
    
    return predicates_set


def extract_let_definitions(node, definitions=None):
    """Extract all LET definitions with their predicates."""
    if definitions is None:
        definitions = []
    
    if not isinstance(node, dict):
        return definitions
    
    if node.get("constructor") == "Let":
        definitions.append({
            "name": node.get("name", "Unknown"),
            "type": node.get("type", ""),
            "predicates": extract_predicates(node.get("body", {}))
        })
        # Continue in the "in" clause
        extract_let_definitions(node.get("in"), definitions)
    else:
        # Recursively search in all dict/list values
        for value in node.values():
            if isinstance(value, (dict, list)):
                extract_let_definitions(value, definitions)
    
    return definitions


def extract_let_definitions_normal(lets_array):
    """Extract LET definitions from normal JSON format (from 'lets' array)."""
    return [{
        "name": let_def.get("e", "Unknown"),
        "type": let_def.get("enftype", ""),
        "predicates": extract_predicates(let_def.get("formula", {}))
    } for let_def in lets_array]


def extract_implications(node, implications=None):
    """Extract all implications (Imp) from formula with predicates on left and right."""
    if implications is None:
        implications = []
    
    if isinstance(node, list):
        for item in node:
            extract_implications(item, implications)
        return implications
    
    if not isinstance(node, dict):
        return implications
    
    if node.get("constructor") == "Imp":
        implications.append({
            "left": extract_predicates(node.get("left", {})),
            "right": extract_predicates(node.get("right", {}))
        })
    
    # Recursively search in all dict/list values
    for value in node.values():
        if isinstance(value, (dict, list)):
            extract_implications(value, implications)
    
    return implications


def extract_top_level_rules(instrs):
    """Extract top-level rules from the first instruction's effects list.
    
    Returns a list of rules where each rule has:
    - id: unique identifier (index in the effects list)
    - type: CauByCau or CauBySup
    - filter: set of predicates in the filter
    - effects: set of predicates in the effects
    - events: dict mapping predicate name to monotonicity ("Monotonic", "Antimonotonic", etc.)
    """
    if not instrs or len(instrs) == 0:
        return []
    
    first_instr = instrs[0]
    recipe = first_instr.get("recipe", {})
    by_field = recipe.get("by", {})
    effects_list = by_field.get("effects", [])
    
    rules = []
    for idx, effect_item in enumerate(effects_list):
        if not isinstance(effect_item, dict):
            continue
        
        # Each effect is an NInstructions with nested instructions
        if effect_item.get("constructor") == "NInstructions":
            instructions = effect_item.get("instructions", [])
            
            # Get the first instruction's recipe
            if instructions and "recipe" in instructions[0]:
                recipe = instructions[0]["recipe"]
                recipe_by = recipe.get("by", {})
                rule_type = recipe.get("constructor", "Unknown")
                
                # Extract events with monotonicity information
                events_list = recipe_by.get("events", [])
                events_dict = {event["name"]: event["polarity"] for event in events_list}
                
                rule = {
                    "id": idx,
                    "type": rule_type,
                    "filter": extract_predicates(recipe_by.get("filter", {})),
                    "effects": extract_predicates(recipe_by.get("effects", {})),
                    "events": events_dict
                }
                rules.append(rule)
    
    return rules


def extract_causality_rules(node, rules=None):
    """Extract all CauByCau and CauBySup rules with predicates from filter and effects."""
    if rules is None:
        rules = []
    
    if isinstance(node, list):
        for item in node:
            extract_causality_rules(item, rules)
        return rules
    
    if not isinstance(node, dict):
        return rules
    
    constructor = node.get("constructor")
    if constructor in ["CauByCau", "CauBySup"]:
        by_field = node.get("by", {})
        rules.append({
            "type": constructor,
            "filter": extract_predicates(by_field.get("filter", {})),
            "effects": extract_predicates(by_field.get("effects", {}))
        })
    
    # Recursively search in all dict/list values
    for value in node.values():
        if isinstance(value, (dict, list)):
            extract_causality_rules(value, rules)
    
    return rules
