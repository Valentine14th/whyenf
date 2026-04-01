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

### Prerequisites
First, build enfguard:
```bash
cd /home/runner/work/whyenf/whyenf
dune build
```

### Testing a Single Log
To verify a test log triggers the expected rule:

```bash
# Method 1: Use the helper script
./test_single_log.sh art5_1a_lawfulness

# Method 2: Run enfguard directly
./enfguard -sig ressources/minitwit/minitwit_gdpr.sig \
           -formula ressources/minitwit/minitwit_gdpr.mfotl \
           -func ressources/gdpr.py \
           -label \
           -log ressources/minitwit/test_logs/testable/art5_1a_lawfulness.log
```

Look for `[Enforcer:Label]` lines in the output to verify the rule was triggered.

### Verifying All Logs
To run all tests and generate a verification report:

```bash
./verify_testable_logs.py
```

This will:
1. Run enfguard on each test log
2. Check if the expected label(s) appear in the output
3. Generate a summary report
4. Save detailed results to `verification_report.json`

## Test Organization

Based on analyze_testability.py results, the following testable rules are covered:

### Expected Labels by Test

Each test is expected to trigger specific label(s) in the gdpr.lex file:

#### Article 5: Principles
- `art5_1a_lawfulness.log` → gdpr.lex:161:1-169:54 (lawfulness)
- `art5_1b_purpose_must_exist.log` → gdpr.lex:173:1-179:54 (must have purpose)
- `art5_1b_legitimate_purpose.log` → gdpr.lex:181:1-188:54 (legitimate purpose)
- `art5_1b_compatible_purpose.log` → gdpr.lex:190:1-196:54 (purpose compatibility)
- `art5_1c_minimization.log` → gdpr.lex:212:1-221:54 (data minimization)
- `art5_1d_accuracy.log` → gdpr.lex:225:1-232:54 (accuracy)
- `art5_1d_accuracy_causing.log` → gdpr.lex:234:1-240:45 (cause rectify/delete)
- `art5_1e_storage.log` → gdpr.lex:244:1-251:54 (storage limitation)
- `art5_1f_security.log` → gdpr.lex:262:1-267:54 (security)

#### Article 7: Consent Conditions
- `art7_1_demonstrate.log` → gdpr.lex:469:1-476:54 (demonstrate consent)
- `art7_2_format.log` → gdpr.lex:482:1-489:45 (consent format)
- `art7_3_withdrawal_info.log` → gdpr.lex:525:1-530:45 (inform withdrawal)
- `art7_3_withdrawal.log` → gdpr.lex:161:1-169:54 (handle withdrawal)

#### Article 8: Child Consent
- `art8_2_child.log` → gdpr.lex:588:1-594:54 (check not child)

#### Article 9: Special Data
- `art9_1_prohibition.log` → gdpr.lex:722:1-728:45 (prohibition)
- `art9_2a_explicit_consent.log` → gdpr.lex:722:1-728:45 (explicit consent)

#### Articles 12-22: Data Subject Rights
- `art12_3_response_time.log` → gdpr.lex:985:1-990:45 (response timing)
- `art12_3_extension.log` → gdpr.lex:992:1-997:52, gdpr.lex:1007:1-1012:38 (extension)
- `art12_4_refusal.log` → gdpr.lex:1034:1-1039:38 (refusal)
- `art12_5_fees.log` → gdpr.lex:1056:1-1061:52 (fees)
- `art13_1a_identity.log` → gdpr.lex:1084:1-1092:45 (controller identity)
- `art13_1b_dpo.log` → gdpr.lex:1106:1-1114:45 (DPO contact)
- `art13_1c_purposes.log` → gdpr.lex:1128:1-1138:45 (purposes/legal basis)
- `art13_1d_interests.log` → gdpr.lex:1148:1-1157:45 (legitimate interests)
- `art13_1e_recipients.log` → gdpr.lex:1181:1-1189:45, gdpr.lex:1191:1-1199:45 (recipients)
- `art13_2a_storage.log` → gdpr.lex:1264:1-1271:54 (storage criteria)
- `art13_2b_rights.log` → gdpr.lex:1318:1-1325:45 (data subject rights)
- `art13_2c_withdrawal.log` → gdpr.lex:1329:1-1337:45 (withdrawal right)
- `art13_2d_complaint.log` → gdpr.lex:1345:1-1352:45 (complaint right)
- `art13_2e_requirement.log` → gdpr.lex:1371:1-1379:45 (statutory requirement)
- `art13_2f_automated.log` → gdpr.lex:1408:1-1415:54 (automated decision)
- `art14_1f_source.log` → gdpr.lex:1490:1-1496:45 (data source)
- `art15_access.log` → gdpr.lex:1954:1-1961:45 (access request)
- `art16_rectify.log` → gdpr.lex:1993:1-1998:45 (rectification)
- `art17_erase.log` → gdpr.lex:2036:1-2041:45 (erasure)
- `art18_restrict.log` → gdpr.lex:2254:1-2262:54 (restriction)
- `art19_notify_rectification.log` → gdpr.lex:2302:1-2308:45 (notify rectification)
- `art19_notify_erasure.log` → gdpr.lex:2310:1-2316:45 (notify erasure)
- `art19_notify_restriction.log` → gdpr.lex:2318:1-2324:45 (notify restriction)
- `art20_portability.log` → gdpr.lex:2368:1-2375:31 (portability)
- `art21_object.log` → gdpr.lex:2036:1-2041:45 (objection)
- `art22_automated.log` → gdpr.lex:2506:1-2512:54 (automated decision)

#### Article 30: Records of Processing
- `art30_records.log` → gdpr.lex:2616:1-2621:45 (activity records)

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
