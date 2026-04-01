#!/usr/bin/env python3
"""
Analyze which GDPR tests are actually testable given the MiniTwit refinement assumes.
Highlights rules that appear in the compiled MFOTL file.
"""

import re
from pathlib import Path
from typing import Set, Dict, List, Tuple
from collections import defaultdict

class RuleParser:
    """Parse rules from gdpr.lex file."""
    
    def __init__(self, gdpr_file: Path):
        self.content = gdpr_file.read_text()
        self.lines = self.content.splitlines()
        
    def parse_all_rules(self) -> Dict[str, Dict]:
        """Parse all rules and return structured data."""
        rules = {}
        i = 0
        
        while i < len(self.lines):
            line = self.lines[i].strip()
            
            # Check if this is a rule definition
            if line.startswith('rule'):
                rule_data = self._parse_single_rule(i)
                if rule_data:
                    rules[rule_data['name']] = rule_data
                    i = rule_data['end_line']
                else:
                    i += 1
            else:
                i += 1
        
        return rules
    
    def _parse_single_rule(self, start_line: int) -> Dict:
        """Parse a single rule starting at the given line."""
        line = self.lines[start_line].strip()
        
        # Extract rule name
        name_match = re.match(r'rule\s+"([^"]+)"', line)
        if name_match:
            rule_name = name_match.group(1)
        else:
            rule_name = f"anonymous_rule_{start_line}"
        
        # Find the end of the rule (next rule, article, paragraph, or point)
        end_line = start_line + 1
        indent_level = len(self.lines[start_line]) - len(self.lines[start_line].lstrip())
        
        while end_line < len(self.lines):
            current_line = self.lines[end_line].strip()
            current_indent = len(self.lines[end_line]) - len(self.lines[end_line].lstrip())
            
            # Check for end markers
            if current_indent <= indent_level and current_line:
                if (current_line.startswith('rule') or 
                    current_line.startswith('article') or
                    current_line.startswith('paragraph') or
                    current_line.startswith('point') or
                    current_line.startswith('note')):
                    break
            
            end_line += 1
        
        # Extract the full rule text
        rule_text = '\n'.join(self.lines[start_line:end_line])
        
        # Parse whenever clause (conditions)
        conditions = self._extract_predicates_from_whenever(rule_text)
        
        # Parse oblige/constitute/except clauses (effects)
        effects = self._extract_predicates_from_effects(rule_text)
        
        # Determine rule type
        rule_type = self._determine_rule_type(rule_text)
        
        return {
            'name': rule_name,
            'start_line': start_line + 1,  # 1-indexed
            'end_line': end_line,
            'text': rule_text,
            'conditions': conditions,
            'effects': effects,
            'type': rule_type
        }
    
    def _extract_predicates_from_whenever(self, rule_text: str) -> Set[str]:
        """Extract predicates from the whenever clause."""
        predicates = set()
        
        # Find whenever clause
        whenever_match = re.search(r'whenever\s+(.*?)(?:oblige|constitute|except)', rule_text, re.DOTALL)
        if whenever_match:
            whenever_clause = whenever_match.group(1)
            # Extract all predicates (CapitalizedWords followed by parenthesis)
            for match in re.finditer(r'\b([A-Z][a-zA-Z]+)\s*\(', whenever_clause):
                predicates.add(match.group(1))
        
        return predicates
    
    def _extract_predicates_from_effects(self, rule_text: str) -> Set[str]:
        """Extract predicates from oblige/constitute/except clauses."""
        predicates = set()
        
        # Find oblige/constitute clauses
        for keyword in ['oblige', 'constitute', 'except']:
            pattern = f'{keyword}\\s+(.*?)(?:transparently enforceable|enforceable|$)'
            matches = re.finditer(pattern, rule_text, re.DOTALL)
            for match in matches:
                clause = match.group(1)
                # Extract all predicates
                for pred_match in re.finditer(r'\b([A-Z][a-zA-Z]+)\s*\(', clause):
                    predicates.add(pred_match.group(1))
        
        return predicates
    
    def _determine_rule_type(self, rule_text: str) -> str:
        """Determine if rule is constitute, oblige, or except."""
        if 'constitute' in rule_text:
            return 'constitute'
        elif 'except' in rule_text:
            return 'except'
        elif 'oblige' in rule_text:
            return 'oblige'
        return 'unknown'


def load_assume_false_predicates(rex_file: Path) -> Set[str]:
    """Load all 'assume false' predicates from refinement file."""
    assume_false = set()
    with open(rex_file) as f:
        for line in f:
            match = re.search(r'assume false (\w+)', line)
            if match:
                assume_false.add(match.group(1))
    return assume_false


def load_mfotl_line_ranges(mfotl_file: Path) -> Set[int]:
    """
    Extract all line numbers from MFOTL file labels.
    Labels look like: {"example/GDPR/gdpr.lex:1681:1-1690:45"}
    Returns a set of all start line numbers that appear in the MFOTL.
    """
    line_numbers = set()
    if not mfotl_file.exists():
        return line_numbers
    
    with open(mfotl_file) as f:
        for line in f:
            # Find all patterns like gdpr.lex:START:1-END:COL
            matches = re.finditer(r'gdpr\.lex:(\d+):\d+-(\d+):\d+', line)
            for match in matches:
                start_line = int(match.group(1))
                line_numbers.add(start_line)
    
    return line_numbers


def build_constitute_graph(rules: Dict[str, Dict]) -> Dict[str, List[str]]:
    """Build a graph of constitute rules: predicate -> [rules that constitute it]."""
    constitute_graph = defaultdict(list)
    
    for rule_name, rule_data in rules.items():
        if rule_data['type'] == 'constitute':
            # Get the predicate being constituted (in effects)
            for predicate in rule_data['effects']:
                constitute_graph[predicate].append(rule_name)
    
    return constitute_graph


def is_testable(rule_data: Dict, assume_false: Set[str], 
                constitute_graph: Dict[str, List[str]], 
                all_rules: Dict[str, Dict]) -> Tuple[bool, List[str], str]:
    """
    Determine if a rule is testable given assume false predicates.
    
    Returns:
        (is_testable, blocking_predicates, reason)
    """
    # Check predicates in CONDITIONS only
    condition_predicates = rule_data['conditions']
    
    # Find which condition predicates are assumed false
    direct_blockers = [p for p in condition_predicates if p in assume_false]
    
    if not direct_blockers:
        return True, [], "No blocking predicates in conditions"
    
    # Check if any blocker has alternative constitute rules
    bypassable_blockers = []
    real_blockers = []
    
    for blocker in direct_blockers:
        # Check if there are constitute rules for this predicate
        constitute_rules = constitute_graph.get(blocker, [])
        
        if constitute_rules:
            # Check if any constitute rule is testable
            any_testable = False
            for const_rule_name in constitute_rules:
                const_rule = all_rules[const_rule_name]
                # Recursively check (but avoid infinite loops)
                const_conditions = const_rule['conditions']
                const_blockers = [p for p in const_conditions if p in assume_false]
                if not const_blockers:
                    any_testable = True
                    break
            
            if any_testable:
                bypassable_blockers.append(blocker)
            else:
                real_blockers.append(blocker)
        else:
            real_blockers.append(blocker)
    
    if real_blockers:
        return False, real_blockers, "Blocked by assume false in conditions"
    else:
        return True, bypassable_blockers, "Blocking predicates have alternative constitute rules"


def main():
    # Load assume false predicates
    rex_file = Path("ressources/minitwit/minitwit_gdpr.rex")
    assume_false_predicates = load_assume_false_predicates(rex_file)
    
    print(f"Found {len(assume_false_predicates)} 'assume false' predicates:")
    print(sorted(assume_false_predicates))
    print()
    
    # Load MFOTL line ranges
    mfotl_file = Path("ressources/minitwit/minitwit_gdpr_pretty.mfotl")
    mfotl_line_numbers = load_mfotl_line_ranges(mfotl_file)
    print(f"Found {len(mfotl_line_numbers)} rules referenced in MFOTL file")
    print()
    
    # Parse all rules from gdpr.lex
    gdpr_file = Path("ressources/gdpr/gdpr.lex")
    parser = RuleParser(gdpr_file)
    all_rules = parser.parse_all_rules()
    
    print(f"Parsed {len(all_rules)} rules from gdpr.lex")
    print()
    
    # Build constitute graph
    constitute_graph = build_constitute_graph(all_rules)
    print(f"Found {len(constitute_graph)} predicates with constitute rules")
    print()
    
    # Analyze each rule
    print("=" * 80)
    print("TESTABILITY ANALYSIS")
    print("=" * 80)
    print()
    
    testable = []
    untestable = []
    testable_with_alternatives = []
    mfotl_testable = []
    mfotl_untestable = []
    
    for rule_name in sorted(all_rules.keys()):
        rule_data = all_rules[rule_name]
        in_mfotl = rule_data['start_line'] in mfotl_line_numbers
        
        is_test, blockers, reason = is_testable(
            rule_data, assume_false_predicates, constitute_graph, all_rules
        )
        
        # Add MFOTL marker if rule appears in compiled formula
        mfotl_marker = "🔍 " if in_mfotl else ""
        
        if is_test:
            if blockers:
                testable_with_alternatives.append((rule_name, blockers, reason))
                print(f"{mfotl_marker}⚠️  {rule_name} (line {rule_data['start_line']})")
                print(f"   {reason}")
                print(f"   Bypassable: {', '.join(blockers)}")
            else:
                testable.append(rule_name)
                if in_mfotl:
                    mfotl_testable.append(rule_name)
                print(f"{mfotl_marker}✅ {rule_name} (line {rule_data['start_line']})")
            print()
        else:
            untestable.append((rule_name, blockers))
            if in_mfotl:
                mfotl_untestable.append((rule_name, blockers))
            print(f"{mfotl_marker}❌ {rule_name} (line {rule_data['start_line']})")
            print(f"   Blocked by: {', '.join(blockers)}")
            print(f"   Conditions: {', '.join(rule_data['conditions'])}")
            print()
    
    # Summary
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"Total rules analyzed: {len(all_rules)}")
    print(f"✅ Fully testable: {len(testable)}")
    print(f"⚠️  Testable with alternatives: {len(testable_with_alternatives)}")
    print(f"❌ Untestable: {len(untestable)}")
    print()
    
    print("=" * 80)
    print("MFOTL RULES (rules compiled into monitor formula)")
    print("=" * 80)
    print(f"🔍 Rules in MFOTL: {len(mfotl_line_numbers)}")
    print(f"✅ MFOTL rules that are testable: {len(mfotl_testable)}")
    print(f"❌ MFOTL rules that are untestable: {len(mfotl_untestable)}")
    
    if len(mfotl_line_numbers) > 0:
        testability_rate = len(mfotl_testable) / len(mfotl_line_numbers) * 100
        print(f"📊 MFOTL testability rate: {testability_rate:.1f}%")
    print()
    
    if mfotl_untestable:
        print("⚠️  MFOTL rules that are UNTESTABLE:")
        for rule_name, blockers in mfotl_untestable:
            print(f"  - {rule_name}: {', '.join(blockers)}")
        print()
    
    if untestable:
        print("All untestable rules:")
        for rule_name, blockers in untestable:
            print(f"  - {rule_name}: {', '.join(blockers)}")


if __name__ == "__main__":
    main()
