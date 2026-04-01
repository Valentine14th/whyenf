#!/usr/bin/env python3
"""
Enhanced testability analysis with grouping by article.
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
        current_article = None
        i = 0
        
        while i < len(self.lines):
            line = self.lines[i].strip()
            
            # Track current article
            if line.startswith('article'):
                match = re.match(r'article\s+"(\d+)"', line)
                if match:
                    current_article = match.group(1)
            
            # Check if this is a rule definition
            if line.startswith('rule'):
                rule_data = self._parse_single_rule(i, current_article)
                if rule_data:
                    rules[rule_data['name']] = rule_data
                    i = rule_data['end_line']
                else:
                    i += 1
            else:
                i += 1
        
        return rules
    
    def _parse_single_rule(self, start_line: int, article: str) -> Dict:
        """Parse a single rule starting at the given line."""
        line = self.lines[start_line].strip()
        
        # Extract rule name
        name_match = re.match(r'rule\s+"([^"]+)"', line)
        if name_match:
            rule_name = name_match.group(1)
        else:
            rule_name = f"anonymous_rule_{start_line}"
        
        # Find the end of the rule
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
            'article': article,
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
            # Extract all predicates
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
    
    print(f"Found {len(assume_false_predicates)} 'assume false' predicates")
    print()
    
    # Parse all rules from gdpr.lex
    gdpr_file = Path("ressources/gdpr/gdpr.lex")
    parser = RuleParser(gdpr_file)
    all_rules = parser.parse_all_rules()
    
    print(f"Parsed {len(all_rules)} rules from gdpr.lex")
    print()
    
    # Build constitute graph
    constitute_graph = build_constitute_graph(all_rules)
    
    # Group rules by article
    by_article = defaultdict(list)
    for rule_name, rule_data in all_rules.items():
        article = rule_data.get('article', 'unknown')
        by_article[article].append((rule_name, rule_data))
    
    # Analyze by article
    print("=" * 80)
    print("TESTABILITY ANALYSIS BY ARTICLE")
    print("=" * 80)
    print()
    
    article_stats = {}
    
    for article in sorted(by_article.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        rules_in_article = by_article[article]
        
        testable_count = 0
        untestable_count = 0
        
        for rule_name, rule_data in rules_in_article:
            is_test, blockers, reason = is_testable(
                rule_data, assume_false_predicates, constitute_graph, all_rules
            )
            if is_test and not blockers:
                testable_count += 1
            else:
                untestable_count += 1
        
        total = testable_count + untestable_count
        percentage = (testable_count / total * 100) if total > 0 else 0
        
        article_stats[article] = {
            'total': total,
            'testable': testable_count,
            'untestable': untestable_count,
            'percentage': percentage
        }
        
        print(f"Article {article}: {testable_count}/{total} testable ({percentage:.0f}%)")
    
    print()
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    
    total_rules = len(all_rules)
    total_testable = sum(s['testable'] for s in article_stats.values())
    total_untestable = sum(s['untestable'] for s in article_stats.values())
    
    print(f"Total rules: {total_rules}")
    print(f"✅ Testable: {total_testable} ({total_testable/total_rules*100:.1f}%)")
    print(f"❌ Untestable: {total_untestable} ({total_untestable/total_rules*100:.1f}%)")
    print()
    
    # List most common blockers
    blocker_count = defaultdict(int)
    for rule_name, rule_data in all_rules.items():
        is_test, blockers, reason = is_testable(
            rule_data, assume_false_predicates, constitute_graph, all_rules
        )
        for blocker in blockers:
            blocker_count[blocker] += 1
    
    if blocker_count:
        print("Most common blocking predicates:")
        for blocker, count in sorted(blocker_count.items(), key=lambda x: -x[1])[:15]:
            print(f"  {blocker}: {count} rules")


if __name__ == "__main__":
    main()
