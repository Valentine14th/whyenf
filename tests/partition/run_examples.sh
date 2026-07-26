#!/bin/bash
# Examples of how to run configs in different ways

echo "=== Example 1: Run specific configs in order ==="
echo "python3 run_all_enfflash_configs.py minitwit_enfflash_new_5.yaml minitwit_enfflash_new_10.yaml"
echo ""

echo "=== Example 2: Run configs from a list file ==="
echo "python3 run_all_enfflash_configs.py --config-list configs/quick_test.txt"
echo ""

echo "=== Example 3: Run all configs matching pattern ==="
echo "python3 run_all_enfflash_configs.py --pattern 'minitwit_enfflash_new_*.yaml'"
echo ""

echo "=== Example 4: Dry run to see what would execute ==="
echo "python3 run_all_enfflash_configs.py --config-list configs/example_run_order.txt --dry-run"
echo ""

echo "=== Example 5: Continue on error ==="
echo "python3 run_all_enfflash_configs.py --continue-on-error"
echo ""

echo "Select which example to run (1-5) or 'q' to quit:"
read -r choice

case $choice in
    1)
        python3 run_all_enfflash_configs.py minitwit_enfflash_new_5.yaml minitwit_enfflash_new_10.yaml
        ;;
    2)
        python3 run_all_enfflash_configs.py --config-list configs/quick_test.txt
        ;;
    3)
        python3 run_all_enfflash_configs.py --pattern "minitwit_enfflash_new_*.yaml"
        ;;
    4)
        python3 run_all_enfflash_configs.py --config-list configs/example_run_order.txt --dry-run
        ;;
    5)
        python3 run_all_enfflash_configs.py --continue-on-error
        ;;
    q|Q)
        echo "Exiting"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
