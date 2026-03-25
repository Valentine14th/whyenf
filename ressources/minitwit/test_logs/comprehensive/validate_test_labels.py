#!/usr/bin/env python3
"""
Validate that test logs trigger their expected GDPR rule labels.
Checks if the expected label appears in the result JSON files.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Set

# Mapping of test name → expected label(s)
# Labels are in format: example/GDPR/gdpr.lex:LINE:COL-LINE:COL
TEST_LABEL_MAPPING = {
    # Article 5(1)(a) - Lawfulness
    "art5_1a_missing_lawful_basis": [
        "example/GDPR/gdpr.lex:161:1-169:54"  # lawfulness rule
    ],
    
    # Article 5(1)(b) - Purpose limitation
    "art5_1b_must_have_purpose": [
        "example/GDPR/gdpr.lex:173:1-179:54"  # must_have_purpose
    ],
    "art5_1b_illegitimate_purpose": [
        "example/GDPR/gdpr.lex:181:1-188:54"  # purpose_conditions (IsLegitimate)
    ],
    "art5_1b_purpose_limitation": [
        "example/GDPR/gdpr.lex:190:1-196:54"  # purpose_limitation
    ],
    
    # Article 5(1)(c) - Data minimization
    "art5_1c_data_minimization": [
        "example/GDPR/gdpr.lex:212:1-221:54"  # data minimization rule
    ],
    
    # Article 5(1)(d) - Accuracy
    "art5_1d_inaccurate_data": [
        "example/GDPR/gdpr.lex:225:1-232:54"  # accurate_and_up_to_date
    ],
    "art5_1d_accuracy_deletion_trigger": [
        "example/GDPR/gdpr.lex:234:1-240:45"  # accuracy_deletion (causing)
    ],
    
    # Article 5(1)(e) - Storage limitation
    "art5_1e_storage_limitation": [
        "example/GDPR/gdpr.lex:244:1-251:54"  # temporal_storage_limitation
    ],
    
    # Article 5(1)(f) - Security
    "art5_1f_security": [
        "example/GDPR/gdpr.lex:262:1-267:54"  # security rule
    ],
    
    # Article 7(1) - Demonstrate consent
    "art7_1_demonstrate_consent": [
        "example/GDPR/gdpr.lex:469:1-476:54"  # IsAbleToDemonstrateConsent
    ],
    
    # Article 7(2) - Consent request format
    "art7_2_consent_request_format": [
        "example/GDPR/gdpr.lex:482:1-489:45"  # distinguishable consent request
    ],
    
    # Article 7(3) - Withdrawal right
    "art7_3_inform_withdrawal_right": [
        "example/GDPR/gdpr.lex:525:1-530:45"  # inform withdrawal right
    ],
    "art7_3_consent_withdrawal": [
        "example/GDPR/gdpr.lex:161:1-169:54"  # loses lawful basis after revoke
    ],
    
    # Article 8(2) - Child consent
    "art8_2_check_not_child": [
        "example/GDPR/gdpr.lex:588:1-594:54"  # CheckNotChild requirement
    ],
    
    # Article 9(1) - Special data
    "art9_1_special_data_no_consent": [
        "example/GDPR/gdpr.lex:722:1-728:45"  # special data prohibition
    ],
    "art9_2a_special_consent": [
        "example/GDPR/gdpr.lex:722:1-728:45"  # special consent exception
    ],
    
    # Article 12(3) - Request response
    "art12_3_request_response": [
        "example/GDPR/gdpr.lex:985:1-990:45"  # RequestResponse timing
    ],
    "art12_3_request_extension": [
        "example/GDPR/gdpr.lex:992:1-997:52",  # extension conditions
        "example/GDPR/gdpr.lex:1007:1-1012:38"  # inform about extension
    ],
    
    # Article 12(4) - Request refusal
    "art12_4_request_refusal": [
        "example/GDPR/gdpr.lex:1034:1-1039:38"  # RefuseRequest with inform
    ],
    
    # Article 12(5) - Fees
    "art12_5_charge_unfounded": [
        "example/GDPR/gdpr.lex:1056:1-1061:52"  # ChargeForRequest conditions
    ],
    
    # Article 13(1) - Information at collection
    "art13_1a_controller_identity": [
        "example/GDPR/gdpr.lex:1084:1-1092:45"  # controller identity
    ],
    "art13_1b_dpo_contact": [
        "example/GDPR/gdpr.lex:1106:1-1114:45"  # DPO contact
    ],
    "art13_1c_purposes_legal_basis": [
        "example/GDPR/gdpr.lex:1128:1-1138:45"  # purposes
    ],
    "art13_1d_legitimate_interests": [
        "example/GDPR/gdpr.lex:1148:1-1157:45"  # legitimate interests
    ],
    "art13_1e_recipients": [
        "example/GDPR/gdpr.lex:1181:1-1189:45",  # recipients
        "example/GDPR/gdpr.lex:1191:1-1199:45"   # recipient categories
    ],
    
    # Article 13(2) - Further information
    "art13_2a_storage_criteria": [
        "example/GDPR/gdpr.lex:1264:1-1271:54"  # storage period/criteria
    ],
    "art13_2b_data_subject_rights": [
        "example/GDPR/gdpr.lex:1318:1-1325:45"  # inform rights
    ],
    "art13_2c_right_withdraw": [
        "example/GDPR/gdpr.lex:1329:1-1337:45"  # withdraw consent right
    ],
    "art13_2d_right_complaint": [
        "example/GDPR/gdpr.lex:1345:1-1352:45"  # complaint right
    ],
    "art13_2e_statutory_requirement": [
        "example/GDPR/gdpr.lex:1371:1-1379:45"  # statutory requirement
    ],
    "art13_2f_automated_decision": [
        "example/GDPR/gdpr.lex:1408:1-1415:54"  # automated decision info
    ],
    
    # Article 14 - Indirect collection
    "art14_1f_data_source": [
        "example/GDPR/gdpr.lex:1490:1-1496:45"  # data source
    ],
    
    # Article 15 - Right of access
    "art15_access_request": [
        "example/GDPR/gdpr.lex:1954:1-1961:45"  # provide copy
    ],
    
    # Article 16 - Rectification
    "art16_rectification": [
        "example/GDPR/gdpr.lex:1993:1-1998:45"  # cause rectify
    ],
    
    # Article 17 - Erasure
    "art17_erasure": [
        "example/GDPR/gdpr.lex:2036:1-2041:45"  # cause delete
    ],
    
    # Article 18 - Restriction
    "art18_restriction": [
        "example/GDPR/gdpr.lex:2254:1-2262:54"  # restrict processing
    ],
    
    # Article 19 - Notification
    "art19_notify_rectification": [
        "example/GDPR/gdpr.lex:2302:1-2308:45"  # notify rectification
    ],
    "art19_notify_erasure": [
        "example/GDPR/gdpr.lex:2310:1-2316:45"  # notify erasure
    ],
    "art19_notify_restriction": [
        "example/GDPR/gdpr.lex:2318:1-2324:45"  # notify restriction
    ],
    
    # Article 20 - Portability
    "art20_portability": [
        "example/GDPR/gdpr.lex:2368:1-2375:31"  # data portability
    ],
    
    # Article 21 - Objection
    "art21_objection": [
        "example/GDPR/gdpr.lex:2036:1-2041:45"  # stop on objection (leads to delete)
    ],
    
    # Article 22 - Automated decisions
    "art22_automated_decision": [
        "example/GDPR/gdpr.lex:2506:1-2512:54"  # automated decision prohibition
    ],
    
    # Article 30 - Records
    "art30_activity_records": [
        "example/GDPR/gdpr.lex:2616:1-2621:45"  # activity records
    ],
}


def extract_labels_from_json(result_file: Path) -> Set[str]:
    """
    Extract all labels from a result JSON file.
    Looks for [Enforcer:Label] entries.
    """
    labels = set()
    
    try:
        with open(result_file, 'r') as f:
            content = f.read()
            
        # Look for [Enforcer:Label] pattern
        import re
        pattern = r'\[Enforcer:Label\]\s*\{\"([^\"]+)\"\}'
        matches = re.findall(pattern, content)
        
        for match in matches:
            # Strip trailing backslashes if present
            label = match.rstrip('\\')
            labels.add(label)
            
    except Exception as e:
        print(f"  ⚠️  Error reading {result_file}: {e}")
    
    return labels


def validate_test_results(results_dir: Path) -> Dict[str, dict]:
    """
    Validate all test results against expected labels.
    Returns dict with test results.
    """
    validation_results = {}
    
    for test_name, expected_labels in TEST_LABEL_MAPPING.items():
        # Find result file for this test
        result_file = results_dir / f"log_{test_name}" / "result.json"
        
        if not result_file.exists():
            validation_results[test_name] = {
                "status": "MISSING",
                "expected": expected_labels,
                "found": [],
                "message": f"Result file not found: {result_file}"
            }
            continue
        
        # Extract labels from result
        found_labels = extract_labels_from_json(result_file)
        
        # Check if any expected label is present
        matched_labels = []
        for expected in expected_labels:
            if expected in found_labels:
                matched_labels.append(expected)
        
        if matched_labels:
            validation_results[test_name] = {
                "status": "PASS",
                "expected": expected_labels,
                "found": list(found_labels),
                "matched": matched_labels
            }
        else:
            validation_results[test_name] = {
                "status": "FAIL",
                "expected": expected_labels,
                "found": list(found_labels),
                "message": "Expected label(s) not found in results"
            }
    
    return validation_results


def print_validation_report(results: Dict[str, dict]):
    """Print a formatted validation report."""
    
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = sum(1 for r in results.values() if r["status"] == "FAIL")
    missing = sum(1 for r in results.values() if r["status"] == "MISSING")
    total = len(results)
    
    print("\n" + "="*80)
    print("GDPR TEST LABEL VALIDATION REPORT")
    print("="*80)
    
    print(f"\n✅ PASSED: {passed}/{total}")
    print(f"❌ FAILED: {failed}/{total}")
    print(f"⚠️  MISSING: {missing}/{total}")
    
    if failed > 0:
        print("\n" + "-"*80)
        print("FAILED TESTS (Expected labels not triggered):")
        print("-"*80)
        for test_name, result in results.items():
            if result["status"] == "FAIL":
                print(f"\n❌ {test_name}")
                print(f"   Expected labels:")
                for label in result["expected"]:
                    print(f"     - {label}")
                print(f"   Found labels:")
                if result["found"]:
                    for label in result["found"]:
                        print(f"     - {label}")
                else:
                    print(f"     (none)")
    
    if missing > 0:
        print("\n" + "-"*80)
        print("MISSING TESTS (Results not found):")
        print("-"*80)
        for test_name, result in results.items():
            if result["status"] == "MISSING":
                print(f"\n⚠️  {test_name}")
                print(f"   {result['message']}")
    
    if passed > 0:
        print("\n" + "-"*80)
        print("PASSED TESTS:")
        print("-"*80)
        for test_name, result in results.items():
            if result["status"] == "PASS":
                print(f"✅ {test_name}")
                print(f"   Matched labels: {', '.join([l.split(':')[1] for l in result['matched']])}")
    
    print("\n" + "="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate that GDPR test logs trigger their expected rule labels"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="output",
        help="Directory containing test results (default: output)"
    )
    parser.add_argument(
        "--json-output",
        type=str,
        help="Optional: Save validation results to JSON file"
    )
    
    args = parser.parse_args()
    
    results_dir = Path(args.results_dir)
    
    if not results_dir.exists():
        print(f"❌ Results directory not found: {results_dir}")
        print(f"   Please run tests first to generate results.")
        sys.exit(1)
    
    print(f"📁 Validating results in: {results_dir}")
    print(f"🔍 Checking {len(TEST_LABEL_MAPPING)} tests...")
    
    # Run validation
    results = validate_test_results(results_dir)
    
    # Print report
    print_validation_report(results)
    
    # Save JSON if requested
    if args.json_output:
        with open(args.json_output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Validation results saved to: {args.json_output}")
    
    # Exit with error if any tests failed
    failed_count = sum(1 for r in results.values() if r["status"] == "FAIL")
    if failed_count > 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
