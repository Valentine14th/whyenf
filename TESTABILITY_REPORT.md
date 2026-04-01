# GDPR Testability Analysis Report

## Overview

This report analyzes which GDPR rules in `gdpr.lex` are testable given the assumptions made in the MiniTwit refinement (`minitwit_gdpr.rex`).

**Analysis Date:** April 1, 2026

## Methodology

### Rule Parsing
- Parsed all 180 rules from `gdpr.lex`
- Precisely identified rule boundaries (not guessing at fixed line counts)
- Extracted predicates from:
  - **Conditions** (whenever clauses)
  - **Effects** (oblige/constitute/except clauses)

### Testability Criteria
A rule is considered **untestable** if and only if:
1. It has predicates in its **conditions** (whenever clause) that are marked as `assume false` in the refinement
2. AND there are no alternative constitute rules that can satisfy those predicates

**Important:** Predicates in the **effects** (oblige/constitute clauses) do NOT make a rule untestable, even if they are `assume false`. This is because we're testing whether the rule can be triggered, not whether all its effects can be satisfied.

### Constitute Rules
Constitute rules provide alternative ways to satisfy predicates (like OR conditions). If a predicate is `assume false` but has a testable constitute rule, the overall rule can still be tested.

## Overall Results

```
Total rules analyzed: 180
✅ Testable:    110 (61.1%)
❌ Untestable:   70 (38.9%)
```

## Results by Article

| Article | Testable | Total | Percentage |
|---------|----------|-------|------------|
| Article 5  | 9  | 12 | 75% |
| Article 6  | 5  | 8  | 62% |
| Article 7  | 3  | 4  | 75% |
| Article 8  | 0  | 3  | **0%** |
| Article 9  | 10 | 14 | 71% |
| Article 10 | 2  | 2  | **100%** |
| Article 12 | 3  | 11 | **27%** |
| Article 13 | 10 | 13 | 77% |
| Article 14 | 15 | 23 | 65% |
| Article 15 | 11 | 15 | 73% |
| Article 16 | 2  | 2  | **100%** |
| Article 17 | 8  | 11 | 73% |
| Article 18 | 4  | 5  | 80% |
| Article 19 | 4  | 4  | **100%** |
| Article 20 | 2  | 3  | 67% |
| Article 21 | 5  | 7  | 71% |
| Article 22 | 3  | 5  | 60% |
| Article 30 | 7  | 14 | 50% |
| Article 44 | 1  | 1  | **100%** |
| Article 45 | 0  | 1  | **0%** |
| Article 46 | 0  | 9  | **0%** |
| Article 49 | 6  | 13 | 46% |

### Key Observations

- **Fully testable articles**: 10, 16, 19, 44 (100% testability)
- **Completely untestable articles**: 8 (children's consent), 45, 46 (international transfers)
- **Low testability**: Article 12 (27%) - transparency and communication requirements
- **Moderate testability**: Articles 30 (50%), 49 (46%) - record keeping and transfer exceptions

## Most Common Blocking Predicates

The following predicates appear most frequently in untestable rules' conditions:

| Predicate | Rules Blocked | Category |
|-----------|---------------|----------|
| `IsPublicAuthority` | 5 | Public Authority |
| `IsPerformanceOfPublicAuthorityTask` | 5 | Public Authority |
| `EndContract` | 4 | Contracts |
| `StartContract` | 4 | Contracts |
| `IsNecessaryForContract` | 4 | Contracts |
| `IsContractParty` | 4 | Contracts |
| `PrepareContract` | 4 | Contracts |
| `IsReception` | 4 | Data Reception |
| `RequestExtension` | 3 | Request Processing |
| `HasIntendedRecipientCategory` | 3 | Recipients |
| `HasIntendedTransfer` | 3 | Transfers |
| `HasStoragePeriod` | 3 | Storage |
| `Transfer` | 3 | Transfers |
| `IsArchival` | 2 | Archival |
| `IsChild` | 2 | Children |

### Analysis of Blockers

1. **Contract-related predicates** (7 instances): MiniTwit doesn't model contractual relationships
2. **Public authority predicates** (10 instances): MiniTwit is a private company, not a public authority
3. **Transfer predicates** (9 instances): MiniTwit uses `assume false Transfer` - no international transfers
4. **Children predicates** (2 instances): MiniTwit doesn't allow minors to register

## Implications

### For Testing MiniTwit Compliance

The 61.1% testability rate means that:
- ✅ **Most core GDPR requirements are testable**: Purpose limitation, accuracy, access rights, rectification, erasure
- ❌ **Some edge cases are not testable**: Contract-based processing, public authority tasks, international transfers
- ⚠️ **Assumption-dependent**: Results depend on the validity of the 76 `assume false` declarations

### Untestable Rules Are Expected

Many untestable rules are **intentionally** excluded from the MiniTwit model:
- MiniTwit is not a public authority → Public authority rules don't apply
- MiniTwit doesn't process contracts → Contract rules don't apply  
- MiniTwit doesn't transfer data internationally → Transfer rules don't apply
- MiniTwit excludes minors → Children's consent rules don't apply

These untestable rules represent **inapplicable** regulations rather than gaps in compliance.

### Recommendations

1. **Verify `assume true` predicates**: The script only checks `assume false`. Rules may also depend on observables that are `assume true` - these should be validated manually.

2. **Focus testing on testable articles**: Prioritize Articles 5, 13, 15, 16, 17, 19 which have high testability and cover core GDPR rights.

3. **Document inapplicability**: For untestable rules, document why they're not applicable to MiniTwit's business model.

4. **Manual review for Article 12**: Only 27% testable - manual review needed for transparency requirements.

## Generated Files

- `analyze_testability.py` - Detailed analysis script (full output with all rules)
- `analyze_testability_summary.py` - Summary script (article-level statistics)
- `testability_report.txt` - Full detailed output from detailed script

## Usage

```bash
# Run detailed analysis
python3 analyze_testability.py > testability_report.txt

# Run summary analysis  
python3 analyze_testability_summary.py
```
