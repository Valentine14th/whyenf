"""
Utilities for parsing MFOTL files.
"""

import os
import re


def extract_first_leaf_line_number(partition_label):
    """Extract the starting line number from the first leaf in a partition label.
    
    Args:
        partition_label: String like "gdpr.lex:2318:1-2324:45 (18 nodes, 1 leaf)" 
                        or "gdpr.lex:1128:1-1138:45, gdpr.lex:1148:1-1157:45, ..."
    
    Returns:
        str: The line number (e.g., "2318") or None if not found
    """
    # Pattern to match location like "gdpr.lex:2318:1-2324:45"
    # We want to extract the first number after the colon (the starting line)
    match = re.search(r':\d+:\d+-\d+:\d+', partition_label)
    if match:
        # Extract just the starting line number
        location = match.group(0)  # e.g., ":2318:1-2324:45"
        line_match = re.search(r':(\d+):', location)
        if line_match:
            return line_match.group(1)
    return None


def parse_mfotl_file(mfotl_path):
    """Parse an MFOTL file to extract LET definitions and top-level rules.
    
    Args:
        mfotl_path: Path to the MFOTL file
    
    Returns:
        tuple: (let_definitions, rules, let_order)
            - let_definitions: dict mapping LET name to full text
            - rules: list of dicts with keys 'index', 'location', 'text'
            - let_order: list of LET names in their original file order
    """
    with open(mfotl_path, 'r') as f:
        content = f.read()
    
    # Extract LET definitions (ending with " IN ")
    let_definitions = {}
    let_order = []  # Track original order
    # Pattern allows for optional characters (like + or -) between parameter list and =
    let_pattern = r'LET\s+([A-Za-z_][A-Za-z0-9_٭]*)\s*\([^)]*\)[^=]*=\s*.*?\s+IN\s+'
    
    for match in re.finditer(let_pattern, content):
        let_name = match.group(1)
        let_text = match.group(0).strip()
        let_definitions[let_name] = let_text
        let_order.append(let_name)
    
    # Extract top-level rules
    # Rules start with □[0s,∞) (not wrapped in brackets like [□[0s,∞)])
    # Each rule is □[0s,∞) {location}{formula}
    # Rules are separated by ∧:R or ∧:L followed by □[0s,∞)
    rules = []
    
    # Find where rules start (after all LET definitions)
    # Look for the first □[0s,∞) that starts a rule
    rules_match = re.search(r'□\[0s,∞\)', content)
    if not rules_match:
        return let_definitions, rules
    
    # Get the rules section
    rules_section = content[rules_match.start():]
    
    # Split rules on " ∧:R □[0s,∞)" or " ∧:L □[0s,∞)"
    # This will give us individual rule parts
    rule_texts = re.split(r'\s+∧:[RL]\s+□\[0s,∞\)\s+', rules_section)
    
    # Process each rule
    rule_index = 0
    for rule_text in rule_texts:
        # Remove the leading □[0s,∞) from the first rule
        rule_text = re.sub(r'^□\[0s,∞\)\s+', '', rule_text.strip())
        
        if not rule_text:
            continue
        
        # Extract location and formula
        # Pattern: {location}{formula}
        location_match = re.match(r'\{([^}]+)\}', rule_text)
        if not location_match:
            continue
        
        # Keep the original location with quotes
        location_with_quotes = location_match.group(1)
        # Strip quotes for use as map key
        location = location_with_quotes.strip('"')
        
        # Find the formula part (second {...} block)
        after_location = rule_text[location_match.end():]
        if not after_location.startswith('{'):
            continue
        
        # Find matching closing brace for the formula (handle nesting)
        brace_count = 1
        pos = 1
        while pos < len(after_location) and brace_count > 0:
            if after_location[pos] == '{':
                brace_count += 1
            elif after_location[pos] == '}':
                brace_count -= 1
            pos += 1
        
        formula = after_location[1:pos-1]
        # Use original location with quotes in the output text
        full_rule = f"{{{location_with_quotes}}}{{{formula}}}"
        
        rules.append({
            'index': rule_index,
            'location': location,  # Without quotes for matching
            'text': full_rule  # With quotes for output
        })
        rule_index += 1
    
    return let_definitions, rules, let_order


def extract_referenced_lets(rules_text, let_definitions, let_order):
    """Extract all LET definitions referenced in the given rules text.
    
    Args:
        rules_text: String containing the rules
        let_definitions: Dict mapping LET name to full text
        let_order: List of LET names in original file order
    
    Returns:
        tuple: (referenced_lets dict, referenced_order list)
    """
    referenced_lets = {}
    
    for let_name in let_definitions:
        # Check if this LET name appears in the rules text
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(let_name) + r'\b'
        if re.search(pattern, rules_text):
            referenced_lets[let_name] = let_definitions[let_name]
    
    # Recursively find LETs referenced by other LETs
    # Keep iterating until no new LETs are found
    found_new = True
    while found_new:
        found_new = False
        for let_name in list(let_definitions.keys()):
            if let_name in referenced_lets:
                continue
            
            # Check if this LET is referenced by any already-referenced LET
            for ref_let_text in referenced_lets.values():
                pattern = r'\b' + re.escape(let_name) + r'\b'
                if re.search(pattern, ref_let_text):
                    referenced_lets[let_name] = let_definitions[let_name]
                    found_new = True
                    break
    
    # Preserve original order by filtering let_order
    referenced_order = [name for name in let_order if name in referenced_lets]
    
    return referenced_lets, referenced_order


def create_minimal_mfotl(let_definitions, let_order, rules):
    """Create a minimal MFOTL file content with given LETs and rules.
    
    Args:
        let_definitions: Dict mapping LET name to full text
        let_order: List of LET names in original file order
        rules: List of rule dicts with 'text' key
    
    Returns:
        str: Complete MFOTL file content
    """
    lines = []
    
    # Add LET definitions in original order
    for let_name in let_order:
        lines.append(let_definitions[let_name])
    
    # Add top-level rules as a big conjunction, each on a new line
    # Format: □[0s,∞) {loc}{formula} ∧:R □[0s,∞) ...
    if rules:
        for i, rule in enumerate(rules):
            if i == 0:
                lines.append("□[0s,∞) " + rule['text'])
            else:
                lines.append("∧:R □[0s,∞) " + rule['text'])
    
    return '\n'.join(lines)


def generate_partition_mfotl_files(mfotl_file, partitions, partition_labels, rules, output_dir, base_name):
    """Generate minimal MFOTL files for each partition.
    
    Args:
        mfotl_file: Path to the original MFOTL file
        partitions: Dict mapping partition index to set of node IDs
        partition_labels: Dict mapping partition index to label
        rules: List of rules from JSON
        output_dir: Directory where partition files will be saved
        base_name: Base name for the MFOTL partition files
    """
    print(f"\nGenerating partition MFOTL files from {mfotl_file}...")
    
    # Parse the MFOTL file
    let_definitions, mfotl_rules, let_order = parse_mfotl_file(mfotl_file)
    print(f"Parsed {len(let_definitions)} LET definitions and {len(mfotl_rules)} rules")
    
    # Create a mapping from location (path suffix) to MFOTL rule
    mfotl_location_map = {}
    for mfotl_rule in mfotl_rules:
        location = mfotl_rule['location']
        mfotl_location_map[location] = mfotl_rule
    
    # Create mfotl subdirectory inside output directory
    mfotl_output_dir = os.path.join(output_dir, 'mfotl')
    os.makedirs(mfotl_output_dir, exist_ok=True)
    
    # For each partition, generate a minimal MFOTL file
    for partition_idx, node_ids in partitions.items():
        # Find which rules (by label) are in this partition
        partition_mfotl_rules = []
        
        for node_id in node_ids:
            # Node IDs are like "RULE_0", "RULE_1", etc.
            if isinstance(node_id, str) and node_id.startswith("RULE_"):
                try:
                    rule_idx = int(node_id.split("_")[1])
                    if rule_idx < len(rules):
                        json_rule = rules[rule_idx]
                        json_label = json_rule.get('label', '')
                        
                        # Match MFOTL rule by finding one whose location matches the JSON label
                        if json_label in mfotl_location_map:
                            partition_mfotl_rules.append(mfotl_location_map[json_label])
                except (IndexError, ValueError):
                    continue
        
        if not partition_mfotl_rules:
            continue
        
        # Extract referenced LET definitions (preserving original order)
        rules_text = " ".join(rule['text'] for rule in partition_mfotl_rules)
        referenced_lets, referenced_order = extract_referenced_lets(rules_text, let_definitions, let_order)
        
        # Create minimal MFOTL content
        mfotl_content = create_minimal_mfotl(referenced_lets, referenced_order, partition_mfotl_rules)
        
        # Write to file
        partition_label = partition_labels.get(partition_idx, f"partition_{partition_idx}")
        
        # Extract line number from first leaf to use in filename
        line_number = extract_first_leaf_line_number(partition_label)
        if line_number:
            output_path = os.path.join(mfotl_output_dir, f"{base_name}_partition_{line_number}.mfotl")
        else:
            # Fallback to using partition index if no line number found
            output_path = os.path.join(mfotl_output_dir, f"{base_name}_partition_{partition_idx}.mfotl")
        
        with open(output_path, 'w') as f:
            f.write(mfotl_content)
        
        print(f"  Partition {partition_idx} ({partition_label}): {len(partition_mfotl_rules)} rules, {len(referenced_lets)} LETs")
