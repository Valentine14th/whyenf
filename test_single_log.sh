#!/bin/bash
# Helper script to test a single log file with enfguard
# Usage: ./test_single_log.sh <test_name>
# Example: ./test_single_log.sh art5_1a_lawfulness

if [ -z "$1" ]; then
    echo "Usage: $0 <test_name>"
    echo "Example: $0 art5_1a_lawfulness"
    exit 1
fi

TEST_NAME="$1"
LOG_FILE="ressources/minitwit/test_logs/testable/${TEST_NAME}.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file not found: $LOG_FILE"
    exit 1
fi

echo "Testing: $TEST_NAME"
echo "Log file: $LOG_FILE"
echo ""
echo "Running enfguard..."
echo "===================="

./enfguard -sig ressources/minitwit/minitwit_gdpr.sig \
           -formula ressources/minitwit/minitwit_gdpr.mfotl \
           -func ressources/gdpr.py \
           -label \
           -log "$LOG_FILE"

echo ""
echo "===================="
echo "Look for [Enforcer:Label] lines in the output above to verify the rule was triggered."
