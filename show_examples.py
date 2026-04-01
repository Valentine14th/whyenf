#!/usr/bin/env python3
"""
Show examples of testable vs untestable rules with detailed explanations.
"""

import sys
from pathlib import Path
from analyze_testability import RuleParser, load_assume_false_predicates, build_constitute_graph, is_testable

def show_rule_example(rule_name: str, rule_data: dict, is_test: bool, blockers: list, assume_false: set):
    """Display a detailed example of a rule."""
    print("=" * 80)
    print(f"Rule: {rule_name} (Line {rule_data['start_line']})")
    print(f"Article: {rule_data.get('article', 'unknown')}")
    print(f"Type: {rule_data['type']}")
    print(f"Status: {'✅ TESTABLE' if is_test and not blockers else '❌ UNTESTABLE'}")
    print("=" * 80)
    print()
    
    # Show conditions
    print("CONDITIONS (whenever clause):")
    conditions_sorted = sorted(rule_data['conditions'])
    for pred in conditions_sorted:
        if pred in assume_false:
            print(f"  ❌ {pred} [ASSUME FALSE - BLOCKS TESTING]")
        else:
            print(f"  ✓  {pred}")
    if not conditions_sorted:
        print("  (none)")
    print()
    
    # Show effects
    print("EFFECTS (oblige/constitute clause):")
    effects_sorted = sorted(rule_data['effects'])
    for pred in effects_sorted:
        if pred in assume_false:
            print(f"  ⚠️  {pred} [assume false - but in effects, doesn't block testing]")
        else:
            print(f"  →  {pred}")
    if not effects_sorted:
        print("  (none)")
    print()
    
    # Show blockers
    if blockers:
        print(f"BLOCKING PREDICATES: {', '.join(blockers)}")
        print()
    
    # Show rule text (first 300 chars)
    preview = rule_data['text'][:300].strip()
    print("RULE TEXT (preview):")
    print(preview)
    if len(rule_data['text']) > 300:
        print("...")
    print()


def main():
    # Load data
    rex_file = Path("ressources/minitwit/minitwit_gdpr.rex")
    gdpr_file = Path("ressources/gdpr/gdpr.lex")
    
    assume_false = load_assume_false_predicates(rex_file)
    parser = RuleParser(gdpr_file)
    all_rules = parser.parse_all_rules()
    constitute_graph = build_constitute_graph(all_rules)
    
    # Analyze all rules
    testable_examples = []
    untestable_examples = []
    
    for rule_name, rule_data in all_rules.items():
        is_test, blockers, reason = is_testable(
            rule_data, assume_false, constitute_graph, all_rules
        )
        
        if is_test and not blockers:
            testable_examples.append((rule_name, rule_data, is_test, blockers))
        elif not is_test:
            untestable_examples.append((rule_name, rule_data, is_test, blockers))
    
    # Show examples
    print("\n\n")
    print("█" * 80)
    print("EXAMPLES OF TESTABLE RULES")
    print("█" * 80)
    print()
    
    # Show a few interesting testable rules
    interesting_testable = [
        "must_have_purpose",
        "purpose_limitation", 
        "accuracy_deletion",
        "data_copy",
        "notify_erasure"
    ]
    
    for rule_name in interesting_testable:
        if rule_name in all_rules:
            rule_data = all_rules[rule_name]
            is_test, blockers, _ = is_testable(rule_data, assume_false, constitute_graph, all_rules)
            show_rule_example(rule_name, rule_data, is_test, blockers, assume_false)
    
    print("\n\n")
    print("█" * 80)
    print("EXAMPLES OF UNTESTABLE RULES")
    print("█" * 80)
    print()
    
    # Show a few interesting untestable rules
    interesting_untestable = [
        "minor_consent_valid",
        "request_response_extension_condition",
        "last_resort_transfer"
    ]
    
    for rule_name in interesting_untestable:
        if rule_name in all_rules:
            rule_data = all_rules[rule_name]
            is_test, blockers, _ = is_testable(rule_data, assume_false, constitute_graph, all_rules)
            show_rule_example(rule_name, rule_data, is_test, blockers, assume_false)


if __name__ == "__main__":
    main()
