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


def extract_let_definitions_normal(lets_array):
    """Extract LET definitions from normal JSON format (from 'lets' array).
    
    Returns:
        dict: Mapping from LET definition name to definition data
    """
    definitions_dict = {}
    
    for let_def in lets_array:

        
        definition = {
            "name": let_def.get("e", "Unknown"),
            "enftype": let_def.get("enftype", ""),
            "predicates": extract_predicates(let_def.get("formula", {})),
            "events": let_def.get("events", [])  # Keep as list of dicts with name, polarity, effect
        }
        definitions_dict[definition["name"]] = definition
    
    return definitions_dict


def extract_top_level_rules(instrs):
    """Extract top-level rules from the first instruction's effects list.
    
    Returns a list of rules where each rule has:
    - id: unique identifier (index in the effects list)
    - type: CauByCau or CauBySup
    - filter: set of predicates in the filter
    - effects: set of predicates in the effects
    - events: dict mapping predicate name to monotonicity ("Monotonic", "Antimonotonic", etc.)
    - label: original label from the JSON (e.g., "example/GDPR/gdpr.lex:2520:1-2526:54")
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
            
            # Get the first instruction's recipe and label
            if instructions and "recipe" in instructions[0]:
                recipe = instructions[0]["recipe"]
                recipe_by = recipe.get("by", {})
                rule_type = recipe.get("constructor", "Unknown")
                label = instructions[0].get("label", f"RULE_{idx}")
            
                
                rule = {
                    "id": f"RULE_{idx}",
                    "type": rule_type,
                    "filter": extract_predicates(recipe_by.get("filter", {})),
                    "effects": extract_predicates(recipe_by.get("effects", {})),
                    "events": recipe_by.get("events", []),
                    "label": label
                }
                rules.append(rule)
    
    return rules
