# Partition Workflow System

Configuration-based workflow for partitioning MFOTL formulas and running enforcement tests.

## Usage

Run from this directory (`tests/partition/`):
```bash
python run_partition_workflow.py configs/example_config.yaml demo_run
```

Results go to `results/<output_name>/`.

## What It Does

1. Generates JSON from the MFOTL formula
2. Builds the dependency graph and partitions it (`viz/visualize_graph.py`)
3. Runs `enfguard` on each partition, for every log
4. Compares partition output/timing against the unpartitioned formula
5. Writes plots and a JSON summary per log, plus a combined multi-log summary

## Configuration Options

### `input` (required)
- `mfotl`, `signature`, `functions` — paths to the formula, signature, and functions file
- `logs: [...]` — explicit list of log files, **or** `log_directory: "..."` — all `*.log` files in a directory (exactly one of the two)

### `output`
- `save_json` — keep intermediate JSON (default `true`)
- `save_normalized_mfotl` — save a pretty-printed normalized MFOTL (default `false`)

### `visualization`
- `enabled` — generate the graph/partitions (default `false`)
- `merge_strategy` — `"by_descendants"` or `"no_merge"` (required when `enabled`)
- `filter_polarity` — drop polarity edges (default `false`)
- `max_merge_size` — cap partitions merged together, `null` = unlimited (default `null`)
- `merge_single_rule_components` — allow single-rule components to merge (default `true`)

### `partition_execution`
- `enabled` — run `enfguard` on partitions (default `false`)
- `timeout` — seconds per partition/step before killing it
- `partition_dir` — where partition `.mfotl` files live (default `<output_dir>/mfotl`)
- `partition_source_dir` — copy pre-generated partitions from here instead of visualizing (used when `visualization.enabled: false`)
- `label` — pass `-l` for label output (default `false`)
- `step_by_step` — ingest logs one timestamp at a time and plot per-step timing (default `false`)
- `repeat_runs` — repeat each partition run N times for timing (default `1`)
- `filter_log_by_signature` / `use_per_partition_signatures` — use each partition's own signature file, filtered log (default `false`)

### Top-level (optional)
- `visualization_binary`, `enforcement_binary` — `enfguard` binaries to use for each step (default `"enfguard"`, resolved relative to workspace root). `enfguard_binary` sets both for backward compatibility.

## Output Structure

```
results/<output_name>/
├── workflow.log
├── graph.html                      # if visualization.enabled
├── mfotl/                          # partition .mfotl files
├── multi_log_summary.json + summary_*.png
└── log_<log_basename>/             # one per log
    ├── enforcement_results.json
    ├── plots/
    └── partition_outputs/
        └── diff/
```

## Common Use Cases

**Partitions only** (no enforcement):
```yaml
visualization:
  enabled: true
partition_execution:
  enabled: false
```

**Full workflow** (partition + enforcement):
```yaml
visualization:
  enabled: true
partition_execution:
  enabled: true
  timeout: 300
```

**Re-run enforcement** (partitions already exist):
```yaml
visualization:
  enabled: false
partition_execution:
  enabled: true
  partition_source_dir: "existing_output/mfotl"
```

## Dependencies

Python 3.7+, PyYAML, PyVis, NetworkX, Jinja2 (`pip install pyyaml pyvis networkx jinja2`)
