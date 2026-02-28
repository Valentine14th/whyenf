#!/usr/bin/env python3
"""
Pretty print a JSON file with proper indentation.
"""

import json
import sys
import argparse


def pretty_print_json(input_file, output_file, indent=2):
    """Read a JSON file and write it back with pretty formatting."""
    try:
        # Read the JSON file
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Write it back with pretty formatting
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write('\n')  # Add newline at end of file
        
        print(f"Successfully pretty printed JSON from '{input_file}' to '{output_file}'")
        return True
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file - {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Pretty print a JSON file with proper indentation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 pretty_print_json.py input.json output.json
  python3 pretty_print_json.py input.json output.json --indent 4
        '''
    )
    
    parser.add_argument('input', help='Input JSON file path')
    parser.add_argument('output', help='Output JSON file path')
    parser.add_argument('--indent', type=int, default=2,
                        help='Number of spaces for indentation (default: 2)')
    
    args = parser.parse_args()
    
    success = pretty_print_json(args.input, args.output, args.indent)
    sys.exit(0 if success else 1)
