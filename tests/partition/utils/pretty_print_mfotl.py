#!/usr/bin/env python3
"""
Pretty print an MFOTL file with each LET and rule on a new line.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'viz', 'utils'))

from mfotl_parser import parse_mfotl_file


def pretty_print_mfotl(input_file, output_file):
    """Parse and pretty print an MFOTL file."""
    let_definitions, rules, let_order = parse_mfotl_file(input_file)
    
    lines = []
    
    # Add each LET on a new line (in original order)
    for let_name in let_order:
        lines.append(let_definitions[let_name])
    
    # Add rules, each on a new line
    if rules:
        # First rule with leading □[0s,∞)
        lines.append(f"□[0s,∞) {rules[0]['text']}")
        
        # Subsequent rules with ∧:R connector
        for rule in rules[1:]:
            lines.append(f"∧:R □[0s,∞) {rule['text']}")
    
    # Write to output file
    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Pretty printed {len(let_order)} LETs and {len(rules)} rules")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python pretty_print_mfotl.py <input.mfotl> <output.mfotl>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    pretty_print_mfotl(input_file, output_file)
