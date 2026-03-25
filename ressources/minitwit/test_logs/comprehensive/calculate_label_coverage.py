#!/usr/bin/env python3
"""
Calculate label coverage from enforcement results.

This script:
1. Extracts all unique labels from an MFOTL file
2. Searches through all output files in a results folder for [Enforcer:Label] patterns
3. Calculates coverage metrics
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Set, Dict, List
from collections import defaultdict


def extract_labels_from_mfotl(mfotl_path: str) -> Set[str]:
    """Extract all unique labels from an MFOTL file."""
    labels = set()
    label_pattern = re.compile(r'\{\"(example/GDPR/[^}\"]+)\"\}')
    
    with open(mfotl_path, 'r', encoding='utf-8') as f:
        content = f.read()
        matches = label_pattern.findall(content)
        labels.update(matches)
    
    return labels


def extract_labels_from_json_file(json_path: str) -> Set[str]:
    """Extract labels from a single JSON file containing [Enforcer:Label] entries."""
    labels = set()
    label_pattern = re.compile(r'\[Enforcer:Label\].*?\"(example/GDPR/[^\"\\]+)')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = label_pattern.findall(content)
            # Remove any trailing backslashes that might be from JSON escaping
            labels.update(label.rstrip('\\') for label in matches)
    except json.JSONDecodeError:
        # File might not be valid JSON, just search as text
        pass
    except Exception as e:
        print(f"Warning: Could not process {json_path}: {e}")
    
    return labels


def extract_labels_from_results_folder(results_folder: str) -> Dict[str, Set[str]]:
    """
    Extract labels from all files in the results folder.
    Returns a dict mapping subfolder names to sets of labels found.
    """
    results_path = Path(results_folder)
    all_labels = set()
    labels_by_subfolder = defaultdict(set)
    
    # Search for all JSON files recursively
    for json_file in results_path.rglob('*.json'):
        labels = extract_labels_from_json_file(str(json_file))
        all_labels.update(labels)
        
        # Determine subfolder (relative to results_folder)
        try:
            relative_path = json_file.relative_to(results_path)
            if len(relative_path.parts) > 1:
                subfolder = relative_path.parts[0]
                labels_by_subfolder[subfolder].update(labels)
        except ValueError:
            pass
    
    labels_by_subfolder['_all'] = all_labels
    return dict(labels_by_subfolder)


def calculate_coverage(mfotl_labels: Set[str], found_labels: Set[str]) -> Dict:
    """Calculate coverage metrics."""
    total_labels = len(mfotl_labels)
    covered_labels = len(found_labels & mfotl_labels)
    coverage_percentage = (covered_labels / total_labels * 100) if total_labels > 0 else 0
    
    uncovered_labels = mfotl_labels - found_labels
    extra_labels = found_labels - mfotl_labels
    
    return {
        'total_labels': total_labels,
        'covered_labels': covered_labels,
        'coverage_percentage': coverage_percentage,
        'uncovered_labels': sorted(uncovered_labels),
        'extra_labels': sorted(extra_labels),
    }


def print_report(mfotl_labels: Set[str], labels_by_subfolder: Dict[str, Set[str]], 
                 verbose: bool = False):
    """Print a formatted coverage report."""
    print("=" * 80)
    print("LABEL COVERAGE REPORT")
    print("=" * 80)
    print()
    
    # Overall coverage
    all_found = labels_by_subfolder.get('_all', set())
    overall = calculate_coverage(mfotl_labels, all_found)
    
    print(f"Total labels in MFOTL file: {overall['total_labels']}")
    print(f"Unique labels found in results: {len(all_found)}")
    print(f"Labels covered: {overall['covered_labels']}")
    print(f"Coverage: {overall['coverage_percentage']:.2f}%")
    print()
    
    if overall['extra_labels']:
        print(f"Warning: {len(overall['extra_labels'])} labels found in results "
              f"but not in MFOTL file")
        if verbose:
            print("Extra labels:")
            for label in overall['extra_labels'][:10]:
                print(f"  - {label}")
            if len(overall['extra_labels']) > 10:
                print(f"  ... and {len(overall['extra_labels']) - 10} more")
            print()
    
    # Per-subfolder breakdown
    print("-" * 80)
    print("Coverage by subfolder:")
    print("-" * 80)
    
    subfolders = sorted([k for k in labels_by_subfolder.keys() if k != '_all'])
    for subfolder in subfolders:
        labels = labels_by_subfolder[subfolder]
        coverage = calculate_coverage(mfotl_labels, labels)
        print(f"\n{subfolder}:")
        print(f"  Unique labels: {len(labels)}")
        print(f"  Coverage: {coverage['coverage_percentage']:.2f}% "
              f"({coverage['covered_labels']}/{coverage['total_labels']})")
    
    print()
    
    # Uncovered labels
    if verbose and overall['uncovered_labels']:
        print("-" * 80)
        print(f"Uncovered labels ({len(overall['uncovered_labels'])}):")
        print("-" * 80)
        for label in overall['uncovered_labels']:
            print(f"  - {label}")
        print()
    elif overall['uncovered_labels']:
        print(f"\nUncovered labels: {len(overall['uncovered_labels'])}")
        print("Use --verbose to see the list of uncovered labels")
        print()


def save_detailed_report(mfotl_labels: Set[str], labels_by_subfolder: Dict[str, Set[str]], 
                        output_file: str):
    """Save a detailed JSON report."""
    all_found = labels_by_subfolder.get('_all', set())
    overall = calculate_coverage(mfotl_labels, all_found)
    
    report = {
        'summary': {
            'total_labels': overall['total_labels'],
            'unique_labels_found': len(all_found),
            'covered_labels': overall['covered_labels'],
            'coverage_percentage': overall['coverage_percentage'],
        },
        'uncovered_labels': overall['uncovered_labels'],
        'extra_labels': overall['extra_labels'],
        'by_subfolder': {}
    }
    
    subfolders = sorted([k for k in labels_by_subfolder.keys() if k != '_all'])
    for subfolder in subfolders:
        labels = labels_by_subfolder[subfolder]
        coverage = calculate_coverage(mfotl_labels, labels)
        report['by_subfolder'][subfolder] = {
            'unique_labels': len(labels),
            'covered_labels': coverage['covered_labels'],
            'coverage_percentage': coverage['coverage_percentage'],
            'labels': sorted(labels),
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"Detailed report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Calculate label coverage from enforcement results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python calculate_label_coverage.py \\
      --mfotl /path/to/minitwit_gdpr_pretty.mfotl \\
      --results /path/to/results/minitwit_all_logs

  # With verbose output and JSON report
  python calculate_label_coverage.py \\
      --mfotl /path/to/minitwit_gdpr_pretty.mfotl \\
      --results /path/to/results/minitwit_all_logs \\
      --verbose \\
      --output coverage_report.json
        """
    )
    
    parser.add_argument(
        '--mfotl',
        required=True,
        help='Path to the MFOTL file containing label definitions'
    )
    parser.add_argument(
        '--results',
        required=True,
        help='Path to the results folder containing enforcement outputs'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output including uncovered labels'
    )
    parser.add_argument(
        '--output', '-o',
        help='Save detailed JSON report to this file'
    )
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.exists(args.mfotl):
        print(f"Error: MFOTL file not found: {args.mfotl}")
        return 1
    
    if not os.path.exists(args.results):
        print(f"Error: Results folder not found: {args.results}")
        return 1
    
    # Extract labels
    print(f"Extracting labels from MFOTL file: {args.mfotl}")
    mfotl_labels = extract_labels_from_mfotl(args.mfotl)
    print(f"Found {len(mfotl_labels)} labels in MFOTL file")
    print()
    
    print(f"Searching for labels in results folder: {args.results}")
    labels_by_subfolder = extract_labels_from_results_folder(args.results)
    all_found = labels_by_subfolder.get('_all', set())
    print(f"Found {len(all_found)} unique labels in results")
    print()
    
    # Print report
    print_report(mfotl_labels, labels_by_subfolder, args.verbose)
    
    # Save detailed report if requested
    if args.output:
        save_detailed_report(mfotl_labels, labels_by_subfolder, args.output)
    
    return 0


if __name__ == '__main__':
    exit(main())
