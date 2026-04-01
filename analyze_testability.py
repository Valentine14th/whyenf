#!/usr/bin/env python3
"""
Analyze GDPR rules to determine which are testable based on the formalization.

This script analyzes gdpr.lex to identify:
1. Rules that are "transparently enforceable" or "enforceable"
2. Available predicates and events from rex files
3. Which rules can be triggered with available test events

Outputs a list of testable rules with their labels and enforcement types.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


def parse_enforceable_rules(lex_file: str) -> Dict[str, List[Dict]]:
    """
    Parse gdpr.lex file to extract enforceable rules.
    Returns dict mapping enforcement type to list of rules.
    """
    rules = defaultdict(list)
    
    with open(lex_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match enforceable rule annotations
    # Looking for comments like "transparently enforceable causing effects" or "enforceable suppressing condition[0]"
    patterns = [
        (r'transparently enforceable causing effects', 'transparently_enforceable_causing'),
        (r'transparently enforceable suppressing condition\[(\d+)\]', 'transparently_enforceable_suppressing'),
        (r'transparently enforceable suppressing conditions', 'transparently_enforceable_suppressing'),
        (r'enforceable causing effects', 'enforceable_causing'),
        (r'enforceable suppressing condition\[(\d+)\]', 'enforceable_suppressing'),
        (r'enforceable suppressing conditions', 'enforceable_suppressing'),
    ]
    
    # Split into lines for analysis
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        # Check if line contains an enforceable annotation
        for pattern, rule_type in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Try to find the rule name and article
                # Look back a few lines for article/rule context
                context = '\n'.join(lines[max(0, i-10):i+10])
                
                # Extract article number
                article_match = re.search(r'article\s+"([\d.]+)"', context, re.IGNORECASE)
                article = article_match.group(1) if article_match else "unknown"
                
                # Extract rule description
                desc_match = re.search(r'"([^"]{20,})"', context)
                description = desc_match.group(1) if desc_match else ""
                
                rules[rule_type].append({
                    'line': i + 1,
                    'article': article,
                    'description': description[:80],
                    'annotation': pattern,
                    'context': line.strip()
                })
                break
    
    return dict(rules)


def parse_available_events(sig_file: str, rex_file: str) -> Tuple[Set[str], Set[str]]:
    """
    Parse signature and refinement files to get available events and predicates.
    Returns (events, predicates)
    """
    events = set()
    predicates = set()
    
    # Parse sig file
    with open(sig_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('fun') and not line.startswith('//'):
                # Extract event/predicate name
                match = re.match(r'(\w+)\s*\(', line)
                if match:
                    events.add(match.group(1))
    
    # Parse rex file for refined events
    with open(rex_file, 'r', encoding='utf-8') as f:
        content = f.read()
        # Find event definitions
        event_pattern = r'(suppressable|observable|causable)?\s*event\s+(\w+)'
        for match in re.finditer(event_pattern, content):
            events.add(match.group(2))
    
    return events, predicates


def identify_testable_rules_from_comprehensive(comprehensive_readme: str) -> List[Dict]:
    """
    Extract testable rules from the comprehensive tests README.
    """
    testable_rules = []
    
    with open(comprehensive_readme, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract test cases with their expected labels
    # Pattern: **test_name.log**: Description → **action** \n  - Expected label: `label`
    test_pattern = r'\*\*(\w+\.log)\*\*:([^\n]+)\n\s+-\s+Expected labels?:\s+`([^`]+)`'
    
    for match in re.finditer(test_pattern, content, re.MULTILINE):
        test_name = match.group(1).replace('.log', '')
        description = match.group(2).strip()
        label = match.group(3).strip()
        
        testable_rules.append({
            'test_name': test_name,
            'description': description,
            'label': label,
        })
    
    return testable_rules


def main():
    """Main analysis function."""
    print("=" * 80)
    print("TESTABILITY ANALYSIS FOR GDPR RULES")
    print("=" * 80)
    print()
    
    # File paths
    base_path = Path(__file__).parent
    lex_file = base_path / "ressources" / "gdpr" / "gdpr.lex"
    sig_file = base_path / "ressources" / "minitwit" / "minitwit_gdpr.sig"
    rex_file = base_path / "ressources" / "minitwit" / "minitwit_gdpr.rex"
    readme_file = base_path / "ressources" / "minitwit" / "test_logs" / "comprehensive" / "COMPREHENSIVE_TESTS_README.md"
    
    # Check if files exist
    if not lex_file.exists():
        print(f"Error: {lex_file} not found")
        return 1
    
    if not sig_file.exists():
        print(f"Error: {sig_file} not found")
        return 1
        
    if not rex_file.exists():
        print(f"Error: {rex_file} not found")
        return 1
    
    # Parse enforceable rules from lex file
    print(f"Analyzing enforceable rules from: {lex_file}")
    rules = parse_enforceable_rules(str(lex_file))
    
    total_rules = sum(len(v) for v in rules.values())
    print(f"Found {total_rules} enforceable rule annotations")
    print()
    
    # Show breakdown by type
    print("Enforceable Rules by Type:")
    print("-" * 80)
    for rule_type, rule_list in sorted(rules.items()):
        print(f"{rule_type}: {len(rule_list)} rules")
    print()
    
    # Parse available events
    print(f"Analyzing available events from: {sig_file} and {rex_file}")
    events, predicates = parse_available_events(str(sig_file), str(rex_file))
    print(f"Found {len(events)} available events/predicates")
    print()
    
    print("Available Events:")
    print("-" * 80)
    for event in sorted(events):
        print(f"  - {event}")
    print()
    
    # Identify testable rules from comprehensive tests
    if readme_file.exists():
        print(f"Analyzing testable rules from: {readme_file}")
        testable = identify_testable_rules_from_comprehensive(str(readme_file))
        print(f"Found {len(testable)} testable rules with documented tests")
        print()
        
        print("Testable Rules (from Comprehensive Tests):")
        print("-" * 80)
        for rule in testable:
            print(f"  {rule['test_name']}:")
            print(f"    Description: {rule['description'][:70]}")
            print(f"    Label: {rule['label']}")
            print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total enforceable rules: {total_rules}")
    print(f"Available test events: {len(events)}")
    if readme_file.exists():
        print(f"Documented testable rules: {len(testable)}")
    print()
    
    print("TESTABILITY CLASSIFICATION:")
    print("-" * 80)
    print("✅ TESTABLE: Rules that can be triggered with available events")
    print("   - Consent/withdrawal flows (Consent, Revoke, SpecialConsent)")
    print("   - Data processing (Read, Write, Collect)")
    print("   - Data subject requests (RequestAccess, RequestRectification, etc.)")
    print("   - Information requirements (Declaration, HasText, Inform)")
    print("   - Data operations (Delete, Rectify)")
    print("   - Notifications (NotifyErasure, NotifyRectification, NotifyRestriction)")
    print("   - Activity records (ActivityRecord)")
    print()
    print("❌ NON-TESTABLE: Rules requiring unavailable predicates")
    print("   - International transfers (Transfer, IsTransferBasis, etc.)")
    print("   - Contract lifecycle (StartContract, EndContract, etc.)")
    print("   - Archival purposes (IsArchival, IsNecessaryForArchivalPurposes)")
    print("   - Public authority tasks (IsPublicAuthority, etc.)")
    print()
    
    return 0


if __name__ == '__main__':
    exit(main())
