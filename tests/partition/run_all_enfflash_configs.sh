#!/bin/bash

# Script to run all enfflash config.yaml workflows
# Usage: ./run_all_enfflash_configs.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_DIR="${SCRIPT_DIR}/configs"
RESULTS_BASE_DIR="${SCRIPT_DIR}/results"

# Create timestamp for this batch run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BATCH_LOG="${RESULTS_BASE_DIR}/batch_run_${TIMESTAMP}.log"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running all enfflash workflow configs${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Start time: $(date)"
echo -e "Batch log: ${BATCH_LOG}\n"

# Create results directory if it doesn't exist
mkdir -p "${RESULTS_BASE_DIR}"

# Initialize counters
total=0
success=0
failed=0

# Initialize batch log
echo "Batch run started at $(date)" > "${BATCH_LOG}"
echo "========================================" >> "${BATCH_LOG}"
echo "" >> "${BATCH_LOG}"

# Find all enfflash config files (case insensitive)
# Match patterns: minitwit_enfflash*.yaml or *enfflash*.yaml
for config_file in "${CONFIG_DIR}"/minitwit_enfflash*.yaml; do
    # Check if file exists (in case glob doesn't match)
    if [ ! -f "$config_file" ]; then
        continue
    fi
    
    total=$((total + 1))
    
    # Extract config name for output directory
    config_basename=$(basename "$config_file" .yaml)
    output_name="enfflash_${config_basename}_${TIMESTAMP}"
    
    echo -e "\n${YELLOW}[$total] Processing: ${config_basename}${NC}"
    echo -e "Config: ${config_file}"
    echo -e "Output: ${output_name}"
    echo ""
    
    # Log to batch file
    echo "[$total] Config: ${config_basename}" >> "${BATCH_LOG}"
    echo "    File: ${config_file}" >> "${BATCH_LOG}"
    echo "    Output: ${output_name}" >> "${BATCH_LOG}"
    
    # Run the workflow
    if python3 "${SCRIPT_DIR}/run_partition_workflow.py" "$config_file" "$output_name" 2>&1 | tee -a "${BATCH_LOG}"; then
        success=$((success + 1))
        echo -e "${GREEN}✓ Success${NC}" | tee -a "${BATCH_LOG}"
    else
        failed=$((failed + 1))
        echo -e "${RED}✗ Failed${NC}" | tee -a "${BATCH_LOG}"
    fi
    
    echo "" >> "${BATCH_LOG}"
    echo "----------------------------------------" >> "${BATCH_LOG}"
    echo "" >> "${BATCH_LOG}"
done

# Print summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Batch Run Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "End time: $(date)"
echo -e "Total configs processed: ${total}"
echo -e "${GREEN}Successful: ${success}${NC}"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed: ${failed}${NC}"
else
    echo -e "Failed: ${failed}"
fi
echo -e "Batch log: ${BATCH_LOG}"
echo ""

# Write summary to log
echo "" >> "${BATCH_LOG}"
echo "========================================" >> "${BATCH_LOG}"
echo "Batch run completed at $(date)" >> "${BATCH_LOG}"
echo "Total: ${total} | Success: ${success} | Failed: ${failed}" >> "${BATCH_LOG}"
echo "========================================" >> "${BATCH_LOG}"

# Exit with error if any failed
if [ $failed -gt 0 ]; then
    exit 1
fi
