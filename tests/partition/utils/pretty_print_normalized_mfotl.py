#!/usr/bin/env python3
"""
Pretty printer for normalized MFOTL files.
- Keeps LET statements as they are (one per line)
- Splits rules (starting with '[' and containing labels) onto separate lines
"""

import sys
import re


def split_rules_line(line):
    """
    Split a rules line (starting with '[') into separate rules.
    Each rule should be on its own line.
    Rules are separated by ' ∧ {"' pattern at curly brace depth 0
    (between rules, not inside rule content)
    """
    if not line.startswith('['):
        return [line]
    
    # Find all occurrences of ' ∧ {"' at curly brace depth 0
    # The pattern is: [□[0s,∞) {"label1"}{rule1} ∧ {"label2"}{rule2} ∧ ...]
    # At the ` ∧ {"` between rules, we're outside any {}, so depth_curly should be 0
    
    split_positions = []
    depth_curly = 0
    
    i = 0
    while i < len(line):
        char = line[i]
        
        # Track curly brace depth only
        if char == '{':
            depth_curly += 1
        elif char == '}':
            depth_curly -= 1
        
        # Look for ' ∧ {"' when we're at depth 0 (between rules)
        if (depth_curly == 0 and
            i + 5 <= len(line) and line[i:i+5] == ' ∧ {"'):
            split_positions.append(i)
        
        i += 1
    
    if not split_positions:
        # No splits found
        return [line]
    
    # Split the line at these positions
    rules = []
    start = 0
    for pos in split_positions:
        rules.append(line[start:pos])
        start = pos + 1  # Skip the leading space before '∧'
    
    # Add the last rule (from last split position to end)
    rules.append(line[start:])
    
    return rules


def pretty_print_normalized_mfotl(input_file, output_file):
    """
    Read a normalized MFOTL file and pretty print it.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    output_lines = []
    
    for line in lines:
        line = line.rstrip('\n')
        
        if line.startswith('LET ') or line.strip() == '':
            # Keep LET statements and empty lines as is
            output_lines.append(line)
        elif line.startswith('['):
            # This is the rules line - split it
            rules = split_rules_line(line)
            output_lines.extend(rules)
        else:
            # Any other line, keep as is
            output_lines.append(line)
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + '\n')


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 pretty_print_normalized_mfotl.py <input_file> <output_file>")
        print("\nExample:")
        print("  python3 pretty_print_normalized_mfotl.py input.mfotl output.mfotl")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        pretty_print_normalized_mfotl(input_file, output_file)
        print(f"Successfully formatted {input_file} -> {output_file}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
