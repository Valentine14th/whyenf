# Testable GDPR Rules - Minimal Test Logs

## Overview
This directory contains minimal test logs designed to trigger each testable rule in the GDPR formalization.
These logs are simpler and more focused than the comprehensive tests, with each log targeting a specific rule.

## Purpose
- Verify that each testable rule can be triggered
- Provide minimal examples for debugging
- Start with non-compliant sequence, then make it compliant in the same log (where feasible)

## Test Strategy
Each test log follows this pattern:
1. **Non-compliant phase**: Events that violate the rule
2. **Enforcement trigger**: The rule should be triggered by enfguard
3. **Compliant phase** (where possible): Events that satisfy the rule

## Events Used
All logs use only events defined in `minitwit_gdpr.sig`:
- Read, Write, Collect
- Consent, Revoke, SpecialConsent  
- RequestAccess, RequestRectification, ContestAccuracy, RequestObjection
- Declaration, HasText, Inform
- Delete, Rectify
- NotifyErasure, NotifyRectification, NotifyRestriction
- Send, SendFile
- ActivityRecord
- PersonalData, IsSpecialData
- TP (time progression)

## Running Tests
To verify a test log triggers the expected rule:

```bash
cd /home/runner/work/whyenf/whyenf

./enfguard -sig ressources/minitwit/minitwit_gdpr.sig \
           -formula ressources/minitwit/minitwit_gdpr.mfotl \
           -func ressources/gdpr.py \
           -label \
           -log ressources/minitwit/test_logs/testable/{test_name}.log
```

Look for `[Enforcer:Label]` lines in the output to verify the rule was triggered.

## Test Organization

Based on analyze_testability.py results, the following testable rules are covered:

### Article 5: Principles
- Art 5(1)(a) - Lawfulness, fairness, transparency
- Art 5(1)(b) - Purpose limitation
- Art 5(1)(c) - Data minimization
- Art 5(1)(d) - Accuracy
- Art 5(1)(e) - Storage limitation
- Art 5(1)(f) - Security

### Article 7: Consent Conditions
- Art 7(1) - Demonstrate consent
- Art 7(2) - Consent request format
- Art 7(3) - Withdrawal rights

### Article 8: Child Consent
- Art 8(2) - Verify not child

### Article 9: Special Data
- Art 9(1) - Special data prohibition
- Art 9(2)(a) - Explicit consent exception

### Articles 12-22: Data Subject Rights
- Art 12 - Transparency and communication
- Art 13 - Information when collecting data
- Art 14 - Information for indirect collection
- Art 15 - Right of access
- Art 16 - Right to rectification
- Art 17 - Right to erasure
- Art 18 - Right to restriction
- Art 19 - Notification obligations
- Art 20 - Right to data portability
- Art 21 - Right to object
- Art 22 - Automated decisions

### Article 30: Records of Processing
- Art 30(1) - Maintain activity records

## Total
43 minimal test logs covering all testable GDPR rules identified by analyze_testability.py.
