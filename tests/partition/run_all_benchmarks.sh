#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

RUN_ALL_ENFFLASH_CONFIGS="${SCRIPT_DIR}/run_all_enfflash_configs.py"
ENFFLASH_CONFIG_LIST="${SCRIPT_DIR}/configs/example_run_order.txt"
RUN_ALL_SPLITS="${REPO_ROOT}/lex/evaluation/02_case_studies/GDPRSocial/benchmark/run_all_splits.sh"

usage() {
	cat <<'EOF'
Usage: ./run_all_benchmarks.sh [all|splits|enfflash]

Commands:
  all       Run split benchmarks, then enfflash config benchmarks (default)
  splits    Run only the split benchmarks
  enfflash  Run only the enfflash config benchmarks
EOF
}

MODE="${1:-all}"

if [[ $# -gt 1 ]]; then
	usage >&2
	exit 1
fi

case "${MODE}" in
	all|splits|enfflash)
		;;
	-h|--help|help)
		usage
		exit 0
		;;
	*)
		echo "Unknown command: ${MODE}" >&2
		usage >&2
		exit 1
		;;
esac

if [[ "${MODE}" == "all" || "${MODE}" == "splits" ]]; then
	if [[ ! -x "${RUN_ALL_SPLITS}" ]]; then
		echo "Missing or non-executable script: ${RUN_ALL_SPLITS}" >&2
		exit 1
	fi
fi

if [[ "${MODE}" == "all" || "${MODE}" == "enfflash" ]]; then
	if [[ ! -f "${RUN_ALL_ENFFLASH_CONFIGS}" ]]; then
		echo "Missing script: ${RUN_ALL_ENFFLASH_CONFIGS}" >&2
		exit 1
	fi

	if [[ ! -f "${ENFFLASH_CONFIG_LIST}" ]]; then
		echo "Missing config list: ${ENFFLASH_CONFIG_LIST}" >&2
		exit 1
	fi
fi

if [[ "${MODE}" == "all" || "${MODE}" == "splits" ]]; then
	if [[ "${MODE}" == "all" ]]; then
		echo "=== Step 1/2: Running split benchmarks ==="
	else
		echo "=== Running split benchmarks ==="
	fi
	"${RUN_ALL_SPLITS}"
fi

if [[ "${MODE}" == "all" || "${MODE}" == "enfflash" ]]; then
	echo ""
	if [[ "${MODE}" == "all" ]]; then
		echo "=== Step 2/2: Running enfflash config benchmarks ==="
	else
		echo "=== Running enfflash config benchmarks ==="
	fi
	python3 "${RUN_ALL_ENFFLASH_CONFIGS}" --config-list "${ENFFLASH_CONFIG_LIST}"
fi

echo ""
echo "Benchmark run completed successfully."
