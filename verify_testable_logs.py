#!/usr/bin/env python3
"""
Verify that testable logs trigger their expected GDPR rule labels.

This script runs enfguard on each test log and checks for [Enforcer:Label] output.
It then reports which tests successfully triggered enforcement and which didn't.
"""

import subprocess
import sys
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Base paths
BASE_DIR = Path(__file__).parent
TESTABLE_DIR = BASE_DIR / "ressources" / "minitwit" / "test_logs" / "testable"
SIG_FILE = BASE_DIR / "ressources" / "minitwit" / "minitwit_gdpr.sig"
FORMULA_FILE = BASE_DIR / "ressources" / "minitwit" / "minitwit_gdpr.mfotl"
FUNC_FILE = BASE_DIR / "ressources" / "gdpr.py"
ENFGUARD_BIN = BASE_DIR / "enfguard"

# Expected labels for each test (from comprehensive tests documentation)
EXPECTED_LABELS = {
    # Article 5
    "art5_1a_lawfulness": ["example/GDPR/gdpr.lex:161:1-169:54"],
    "art5_1b_purpose_must_exist": ["example/GDPR/gdpr.lex:173:1-179:54"],
    "art5_1b_legitimate_purpose": ["example/GDPR/gdpr.lex:181:1-188:54"],
    "art5_1b_compatible_purpose": ["example/GDPR/gdpr.lex:190:1-196:54"],
    "art5_1c_minimization": ["example/GDPR/gdpr.lex:212:1-221:54"],
    "art5_1d_accuracy": ["example/GDPR/gdpr.lex:225:1-232:54"],
    "art5_1d_accuracy_causing": ["example/GDPR/gdpr.lex:234:1-240:45"],
    "art5_1e_storage": ["example/GDPR/gdpr.lex:244:1-251:54"],
    "art5_1f_security": ["example/GDPR/gdpr.lex:262:1-267:54"],
    
    # Article 7
    "art7_1_demonstrate": ["example/GDPR/gdpr.lex:469:1-476:54"],
    "art7_2_format": ["example/GDPR/gdpr.lex:482:1-489:45"],
    "art7_3_withdrawal_info": ["example/GDPR/gdpr.lex:525:1-530:45"],
    "art7_3_withdrawal": ["example/GDPR/gdpr.lex:161:1-169:54"],
    
    # Article 8
    "art8_2_child": ["example/GDPR/gdpr.lex:588:1-594:54"],
    
    # Article 9
    "art9_1_prohibition": ["example/GDPR/gdpr.lex:722:1-728:45"],
    "art9_2a_explicit_consent": ["example/GDPR/gdpr.lex:722:1-728:45"],
    
    # Article 12
    "art12_3_response_time": ["example/GDPR/gdpr.lex:985:1-990:45"],
    "art12_3_extension": ["example/GDPR/gdpr.lex:992:1-997:52", "example/GDPR/gdpr.lex:1007:1-1012:38"],
    "art12_4_refusal": ["example/GDPR/gdpr.lex:1034:1-1039:38"],
    "art12_5_fees": ["example/GDPR/gdpr.lex:1056:1-1061:52"],
    
    # Article 13
    "art13_1a_identity": ["example/GDPR/gdpr.lex:1084:1-1092:45"],
    "art13_1b_dpo": ["example/GDPR/gdpr.lex:1106:1-1114:45"],
    "art13_1c_purposes": ["example/GDPR/gdpr.lex:1128:1-1138:45"],
    "art13_1d_interests": ["example/GDPR/gdpr.lex:1148:1-1157:45"],
    "art13_1e_recipients": ["example/GDPR/gdpr.lex:1181:1-1189:45", "example/GDPR/gdpr.lex:1191:1-1199:45"],
    "art13_2a_storage": ["example/GDPR/gdpr.lex:1264:1-1271:54"],
    "art13_2b_rights": ["example/GDPR/gdpr.lex:1318:1-1325:45"],
    "art13_2c_withdrawal": ["example/GDPR/gdpr.lex:1329:1-1337:45"],
    "art13_2d_complaint": ["example/GDPR/gdpr.lex:1345:1-1352:45"],
    "art13_2e_requirement": ["example/GDPR/gdpr.lex:1371:1-1379:45"],
    "art13_2f_automated": ["example/GDPR/gdpr.lex:1408:1-1415:54"],
    
    # Article 14
    "art14_1f_source": ["example/GDPR/gdpr.lex:1490:1-1496:45"],
    
    # Article 15
    "art15_access": ["example/GDPR/gdpr.lex:1954:1-1961:45"],
    
    # Article 16
    "art16_rectify": ["example/GDPR/gdpr.lex:1993:1-1998:45"],
    
    # Article 17
    "art17_erase": ["example/GDPR/gdpr.lex:2036:1-2041:45"],
    
    # Article 18
    "art18_restrict": ["example/GDPR/gdpr.lex:2254:1-2262:54"],
    
    # Article 19
    "art19_notify_rectification": ["example/GDPR/gdpr.lex:2302:1-2308:45"],
    "art19_notify_erasure": ["example/GDPR/gdpr.lex:2310:1-2316:45"],
    "art19_notify_restriction": ["example/GDPR/gdpr.lex:2318:1-2324:45"],
    
    # Article 20
    "art20_portability": ["example/GDPR/gdpr.lex:2368:1-2375:31"],
    
    # Article 21
    "art21_object": ["example/GDPR/gdpr.lex:2036:1-2041:45"],
    
    # Article 22
    "art22_automated": ["example/GDPR/gdpr.lex:2506:1-2512:54"],
    
    # Article 30
    "art30_records": ["example/GDPR/gdpr.lex:2616:1-2621:45"],
}


def run_enfguard(log_file: Path) -> Tuple[int, str, str]:
    """
    Run enfguard on a log file and return (returncode, stdout, stderr).
    """
    cmd = [
        str(ENFGUARD_BIN),
        "-sig", str(SIG_FILE),
        "-formula", str(FORMULA_FILE),
        "-func", str(FUNC_FILE),
        "-label",
        "-log", str(log_file)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def extract_labels(output: str) -> List[str]:
    """
    Extract all [Enforcer:Label] entries from enfguard output.
    """
    labels = []
    # Pattern: [Enforcer:Label] ... "example/GDPR/..."
    pattern = r'\[Enforcer:Label\].*?"(example/GDPR/[^"]+)"'
    
    for match in re.finditer(pattern, output):
        label = match.group(1)
        # Clean up any escaped characters
        label = label.replace('\\', '')
        labels.append(label)
    
    return list(set(labels))  # Remove duplicates


def verify_test_log(log_file: Path) -> Dict:
    """
    Verify a single test log by running enfguard and checking labels.
    """
    test_name = log_file.stem
    
    result = {
        'test_name': test_name,
        'log_file': str(log_file),
        'status': 'UNKNOWN',
        'expected_labels': EXPECTED_LABELS.get(test_name, []),
        'found_labels': [],
        'missing_labels': [],
        'extra_labels': [],
        'error': None
    }
    
    # Run enfguard
    returncode, stdout, stderr = run_enfguard(log_file)
    
    if returncode != 0:
        result['status'] = 'ERROR'
        result['error'] = f"enfguard exited with code {returncode}: {stderr}"
        return result
    
    # Extract labels
    found_labels = extract_labels(stdout)
    result['found_labels'] = found_labels
    
    # Check if expected labels are present
    expected = set(result['expected_labels'])
    found = set(found_labels)
    
    result['missing_labels'] = list(expected - found)
    result['extra_labels'] = list(found - expected)
    
    if not result['missing_labels']:
        result['status'] = 'PASS'
    else:
        result['status'] = 'FAIL'
    
    return result


def main():
    """Main verification function."""
    print("=" * 80)
    print("TESTABLE GDPR RULES - VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    # Check if enfguard exists
    if not ENFGUARD_BIN.exists():
        print(f"ERROR: enfguard not found at {ENFGUARD_BIN}")
        print("Please build enfguard first with: dune build")
        return 1
    
    # Check if testable directory exists
    if not TESTABLE_DIR.exists():
        print(f"ERROR: Testable directory not found at {TESTABLE_DIR}")
        return 1
    
    # Get all log files
    log_files = sorted(TESTABLE_DIR.glob("*.log"))
    
    if not log_files:
        print(f"ERROR: No log files found in {TESTABLE_DIR}")
        return 1
    
    print(f"Found {len(log_files)} test logs to verify")
    print()
    
    # Verify each log
    results = []
    for log_file in log_files:
        print(f"Testing {log_file.name}...", end=" ", flush=True)
        result = verify_test_log(log_file)
        results.append(result)
        
        if result['status'] == 'PASS':
            print("✅ PASS")
        elif result['status'] == 'FAIL':
            print(f"❌ FAIL (missing {len(result['missing_labels'])} label(s))")
        else:
            print(f"⚠️  ERROR")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Count results
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    errors = sum(1 for r in results if r['status'] == 'ERROR')
    
    print(f"✅ PASSED: {passed}/{len(results)}")
    print(f"❌ FAILED: {failed}/{len(results)}")
    print(f"⚠️  ERRORS: {errors}/{len(results)}")
    print()
    
    # Show failed tests
    if failed > 0:
        print("-" * 80)
        print("FAILED TESTS (Expected labels not triggered):")
        print("-" * 80)
        for result in results:
            if result['status'] == 'FAIL':
                print(f"\n❌ {result['test_name']}")
                print(f"   Expected labels:")
                for label in result['expected_labels']:
                    print(f"      - {label}")
                print(f"   Found labels:")
                if result['found_labels']:
                    for label in result['found_labels']:
                        print(f"      - {label}")
                else:
                    print(f"      (none)")
                if result['missing_labels']:
                    print(f"   Missing labels:")
                    for label in result['missing_labels']:
                        print(f"      - {label}")
        print()
    
    # Show errors
    if errors > 0:
        print("-" * 80)
        print("TESTS WITH ERRORS:")
        print("-" * 80)
        for result in results:
            if result['status'] == 'ERROR':
                print(f"\n⚠️  {result['test_name']}")
                print(f"   Error: {result['error']}")
        print()
    
    # Save detailed report
    report_file = TESTABLE_DIR / "verification_report.json"
    with open(report_file, 'w') as f:
        json.dump({
            'summary': {
                'total': len(results),
                'passed': passed,
                'failed': failed,
                'errors': errors
            },
            'results': results
        }, f, indent=2)
    
    print(f"Detailed report saved to: {report_file}")
    print()
    
    return 0 if failed == 0 and errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
