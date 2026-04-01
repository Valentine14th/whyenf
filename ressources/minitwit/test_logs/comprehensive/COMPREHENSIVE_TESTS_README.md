# Comprehensive GDPR Rule Coverage Tests

## Overview
Generated 43 test logs to systematically trigger ALL enforceable rules in the GDPR formalization (gdpr.lex).

## Test Organization

### Article 5: Principles (9 tests)

#### 5(1)(a) - Lawfulness, Fairness, Transparency
- **art5_1a_missing_lawful_basis.log**: Process without consent → violates lawfulness → **suppresses DataProcessing**
  - Expected label: `gdpr.lex:161:1-169:54` (lawfulness rule)

#### 5(1)(b) - Purpose Limitation (3 tests)
- **art5_1b_must_have_purpose.log**: Tests that purpose must exist → **suppresses if no HasPurpose**
  - Expected label: `gdpr.lex:173:1-179:54` (must_have_purpose rule)
- **art5_1b_illegitimate_purpose.log**: Use "marketing" (not in {service, personalized_ad, statistics}) → violates IsLegitimate → **suppresses HasPurpose**
  - Expected label: `gdpr.lex:181:1-188:54` (purpose_conditions rule)
- **art5_1b_purpose_limitation.log**: Collect for "service", process for "personalized_ad" → violates CompatibleWithPurpose → **suppresses processing**
  - Expected label: `gdpr.lex:190:1-196:54` (purpose_limitation rule)

#### 5(1)(c) - Data Minimization
- **art5_1c_data_minimization.log**: Tests adequacy/relevance/necessity requirements → **suppresses if not adequate/relevant/necessary**
  - Expected label: `gdpr.lex:212:1-221:54` (data minimization rule)

#### 5(1)(d) - Accuracy (2 tests)
- **art5_1d_inaccurate_data.log**: RequestRectification makes IsAccurate=FALSE → **suppresses further processing**
  - Expected label: `gdpr.lex:225:1-232:54` (accurate_and_up_to_date rule)
- **art5_1d_accuracy_deletion_trigger.log**: Inaccurate data not deleted/rectified → **causes Delete or Rectify**
  - Expected label: `gdpr.lex:234:1-240:45` (accuracy_deletion causing rule)

#### 5(1)(e) - Storage Limitation
- **art5_1e_storage_limitation.log**: Store after consent revoked → violates IsNecessary → **suppresses Stored**
  - Expected label: `gdpr.lex:244:1-251:54` (temporal_storage_limitation rule)

#### 5(1)(f) - Security
- **art5_1f_security.log**: Tests security requirement → **suppresses if not EnsuresAppropriateSecurity**
  - Expected label: `gdpr.lex:262:1-267:54` (security rule)

### Article 7: Consent Conditions (4 tests)

#### 7(1) - Demonstrate Consent
- **art7_1_demonstrate_consent.log**: Tests IsAbleToDemonstrateConsent requirement → **suppresses if cannot demonstrate**
  - Expected label: `gdpr.lex:469:1-476:54` (IsAbleToDemonstrateConsent rule)

#### 7(2) - Consent Request Format
- **art7_2_consent_request_format.log**: Consent declaration contains other matters → **causes distinguishable consent request**
  - Expected label: `gdpr.lex:482:1-489:45` (distinguishable consent request causing)

#### 7(3) - Withdrawal (2 tests)
- **art7_3_inform_withdrawal_right.log**: Give consent → **causes inform about withdrawal right**
  - Expected label: `gdpr.lex:525:1-530:45` (inform withdrawal right causing)
- **art7_3_consent_withdrawal.log**: Process after Revoke → loses lawful basis → **suppresses processing**
  - Expected label: `gdpr.lex:161:1-169:54` (loses lawful basis after revoke)

### Article 8: Child Consent (1 test)

#### 8(2) - Verify Not Child
- **art8_2_check_not_child.log**: Consent without parental authorization → **requires CheckNotChild**
  - Expected label: `gdpr.lex:588:1-594:54` (CheckNotChild requirement)

### Article 9: Special Data (2 tests)

#### 9(1) - Special Data Prohibition
- **art9_1_special_data_no_consent.log**: Process special data without explicit consent → **causes NOT DataProcessing** (suppresses)
  - Expected label: `gdpr.lex:722:1-728:45` (special data prohibition)

#### 9(2)(a) - Explicit Consent Exception
- **art9_2a_special_consent.log**: SpecialConsent allows processing → validates exception works
  - Expected label: `gdpr.lex:722:1-728:45` (special consent exception)

### Article 12: Transparent Information (4 tests)

#### 12(3) - Request Response Time
- **art12_3_request_response.log**: RequestAccess → **causes RequestResponse within 1 month**
  - Expected label: `gdpr.lex:985:1-990:45` (RequestResponse timing)
- **art12_3_request_extension.log**: Complex request → **allows RequestExtension** + **causes inform about extension**
  - Expected labels: `gdpr.lex:992:1-997:52`, `gdpr.lex:1007:1-1012:38` (extension + inform)

#### 12(4) - Request Refusal
- **art12_4_request_refusal.log**: Tests RefuseRequest → **causes inform with reasons and complaint rights**
  - Expected label: `gdpr.lex:1034:1-1039:38` (RefuseRequest with inform)

#### 12(5) - Fees
- **art12_5_charge_unfounded.log**: Unfounded/excessive request → **allows ChargeForRequest with reasonable fee**
  - Expected label: `gdpr.lex:1056:1-1061:52` (ChargeForRequest conditions)

### Article 13: Information When Collecting (11 tests)

All these trigger **causing** enforcement - require Declaration + Inform when collecting data:

#### 13(1) - Required Information at Collection
- **art13_1a_controller_identity.log**: **Causes** inform controller identity
  - Expected label: `gdpr.lex:1084:1-1092:45` (controller identity)
- **art13_1b_dpo_contact.log**: **Causes** inform DPO contact details
  - Expected label: `gdpr.lex:1106:1-1114:45` (DPO contact)
- **art13_1c_purposes_legal_basis.log**: **Causes** inform purposes and legal basis
  - Expected label: `gdpr.lex:1128:1-1138:45` (purposes)
- **art13_1d_legitimate_interests.log**: **Causes** inform legitimate interests (if 6(1)(f) basis)
  - Expected label: `gdpr.lex:1148:1-1157:45` (legitimate interests)
- **art13_1e_recipients.log**: **Causes** inform recipients/categories (for "statistics" → Analytics, Inc.)
  - Expected labels: `gdpr.lex:1181:1-1189:45`, `gdpr.lex:1191:1-1199:45` (recipients)

#### 13(2) - Further Information
- **art13_2a_storage_criteria.log**: **Causes** inform storage period/criteria
  - Expected label: `gdpr.lex:1264:1-1271:54` (storage period/criteria)
- **art13_2b_data_subject_rights.log**: **Causes** inform about rights (access, rectification, erasure, etc.)
  - Expected label: `gdpr.lex:1318:1-1325:45` (inform rights)
- **art13_2c_right_withdraw.log**: **Causes** inform right to withdraw consent
  - Expected label: `gdpr.lex:1329:1-1337:45` (withdraw consent right)
- **art13_2d_right_complaint.log**: **Causes** inform right to lodge complaint with supervisory authority
  - Expected label: `gdpr.lex:1345:1-1352:45` (complaint right)
- **art13_2e_statutory_requirement.log**: **Causes** inform if statutory/contractual requirement
  - Expected label: `gdpr.lex:1371:1-1379:45` (statutory requirement)
- **art13_2f_automated_decision.log**: **Causes** inform about automated decision-making (personalized_ad)
  - Expected label: `gdpr.lex:1408:1-1415:54` (automated decision info)

### Article 14: Indirect Collection (1 test)

#### 14(1)(f) - Data Source
- **art14_1f_data_source.log**: **Causes** inform about source of data (when not collected from subject)
  - Expected label: `gdpr.lex:1490:1-1496:45` (data source)

### Article 15: Right of Access (1 test)

- **art15_access_request.log**: RequestAccess → **causes** provide PersonalDataCopy in commonly used format
  - Expected label: `gdpr.lex:1954:1-1961:45` (provide copy)

### Article 16: Right to Rectification (1 test)

- **art16_rectification.log**: RequestRectification + ContestAccuracy → **causes** Rectify
  - Expected label: `gdpr.lex:1993:1-1998:45` (cause rectify)

### Article 17: Right to Erasure (1 test)

- **art17_erasure.log**: IsErasureRequest → **causes** Delete
  - Expected label: `gdpr.lex:2036:1-2041:45` (cause delete)

### Article 18: Right to Restriction (1 test)

- **art18_restriction.log**: IsRestrictionRequest → **causes** restrict processing
  - Expected label: `gdpr.lex:2254:1-2262:54` (restrict processing)

### Article 19: Notification to Recipients (3 tests)

When data is rectified/erased/restricted and has been disclosed:

- **art19_notify_rectification.log**: After Rectify + Send → **causes** NotifyRectification to recipient
  - Expected label: `gdpr.lex:2302:1-2308:45` (notify rectification)
- **art19_notify_erasure.log**: After Delete + Send → **causes** NotifyErasure to recipient
  - Expected label: `gdpr.lex:2310:1-2316:45` (notify erasure)
- **art19_notify_restriction.log**: After restriction + Send → **causes** NotifyRestriction to recipient
  - Expected label: `gdpr.lex:2318:1-2324:45` (notify restriction)

### Article 20: Right to Data Portability (1 test)

- **art20_portability.log**: IsPortabilityRequest → **causes** provide data in structured, machine-readable format
  - Expected label: `gdpr.lex:2368:1-2375:31` (data portability)

### Article 21: Right to Object (1 test)

- **art21_objection.log**: RequestObjection → **causes** stop processing (unless compelling grounds)
  - Expected label: `gdpr.lex:2036:1-2041:45` (stop on objection - leads to delete)

### Article 22: Automated Decision Making (1 test)

- **art22_automated_decision.log**: Automated decision (personalized_ad) → **causes** prohibition of automated processing
  - Expected label: `gdpr.lex:2506:1-2512:54` (automated decision prohibition)

### Article 30: Records of Processing (1 test)

- **art30_activity_records.log**: Processing activity → **requires** ActivityRecord maintenance
  - Expected label: `gdpr.lex:2616:1-2621:45` (activity records)

## Enforcement Types

### Suppressing Enforcement (Violations that block operations)
Tests that trigger **suppressing condition[0]** - prevent operations when obligations not met:
- Articles 5(1)(a-f): Missing lawfulness/purpose/accuracy/security
- Article 7(1): Cannot demonstrate consent
- Article 9(1): Special data without explicit consent
- Article 12(3): Request extension conditions
- Article 12(5): Charging fees conditions

### Causing Enforcement (Requirements that force actions)
Tests that trigger **causing effects** - force specific actions to occur:
- Article 5(1)(d): Cause Delete/Rectify when data inaccurate
- Article 7(2): Cause distinguishable consent request
- Article 7(3): Cause inform about withdrawal right
- Articles 12-14: Cause Declaration + Inform about various required information
- Articles 15-18: Cause provide access/rectify/erase/restrict
- Article 19: Cause notify recipients
- Articles 20-22: Cause portability/stop objection/inform about automated decisions

## Running All Tests

```bash
cd /home/valentine/ethz/thesis/whyenf

# Create results directories
mkdir -p output

# Run all comprehensive tests (results go to output/ directory)
for log in ressources/minitwit/test_logs/comprehensive/*.log; do
  name=$(basename "$log" .log)
  echo "Running: $name"
  mkdir -p "output/log_${name}"
  ./enfguard -formula ressources/minitwit/minitwit_gdpr.mfotl \
    -sig ressources/minitwit/minitwit_gdpr.sig \
    -log "$log" \
    -json -label > "output/log_${name}/result.json" 2>&1
done

# Calculate coverage
python calculate_label_coverage.py \
  --results-dir output \
  --mfotl-file ressources/minitwit/minitwit_gdpr_pretty.mfotl \
  --output coverage_comprehensive.json
```

## Validating Test Results

After running the tests, use the validation script to verify that each test triggered its expected label(s):

```bash
cd /home/valentine/ethz/thesis/whyenf

# Validate that all tests triggered their expected labels
python validate_test_labels.py --results-dir output

# Optional: Save validation results to JSON
python validate_test_labels.py --results-dir output --json-output validation_report.json
```

The validation script will:
- Check each test's result file in `output/log_{test_name}/output_reference.txt`
- Extract all `[Enforcer:Label]` entries from the results
- Verify that the expected label(s) appear in the results
- Report:
  - ✅ PASS: Expected label found
  - ❌ FAIL: Expected label missing
  - ⚠️ MISSING: Result file not found

Example output:
```
================================================================================
GDPR TEST LABEL VALIDATION REPORT
================================================================================

✅ PASSED: 41/43
❌ FAILED: 2/43
⚠️  MISSING: 0/43

--------------------------------------------------------------------------------
FAILED TESTS (Expected labels not triggered):
--------------------------------------------------------------------------------

❌ art5_1a_missing_lawful_basis
   Expected labels:
     - example/GDPR/gdpr.lex:162:1-169:54
   Found labels:
     (none)
```

## Expected Coverage Improvement

### Baseline (existing tests)
- 14.14% coverage (14/99 labels)
- Focused on compliance scenarios

### After Comprehensive Tests
- **Target**: 80-95% coverage
- **Reason**: 
  - Tests BOTH compliance (causing) AND violations (suppressing)
  - Covers all major GDPR articles with enforceable rules
  - Triggers both paths: when obligations met vs. when violated
  - Tests all data subject rights (15-22)
  - Tests all information requirements (13-14)
  - Tests special data handling (9)
  - Tests consent lifecycle (7)

### Uncovered Labels (Expected)
May still miss labels for:
- Rules with predicates that are "assume false" (transfer, archival, contracts)
- Complex exception scenarios
- Edge cases in Articles 45-49 (international transfers)
- Specific combinations of conditions

## Notes

### Predicate Availability
Tests ONLY use predicates that are:
1. **Implemented events**: Read, Write, Collect, Delete, Rectify, Consent, SpecialConsent, Revoke, Request*, Declaration, HasText, Inform, Send, Notify*, ActivityRecord
2. **Observable predicates** with refinement rules: PersonalData, IsSpecialData, IsAccurate, IsLegitimate, etc.
3. **Assume true** predicates: IsAdequate, IsRelevant, IsNecessary, IsFair, IsTransparent, format predicates

### Avoided Predicates
Tests DO NOT use "assume false" predicates:
- Transfer-related (Transfer, IsReception, etc.)
- Contract-related (StartContract, EndContract, etc.)
- RequestExtension, RefuseRequest (in violation tests)
- IsArchival, IsControllerRepresentative
- Archival purposes, special medical reasons, etc.

## Validation

To verify tests trigger enforcement:
1. Check result.json files for [Enforcer:Label] entries
2. Look for "suppressing" or "causing" in enforcement output
3. Verify each test has at least one enforcement action
4. Compare labels found vs. total 99 labels in minitwit_gdpr_pretty.mfotl
