# Partition Workflow System

Configuration-based workflow for partitioning MFOTL formulas and running enforcement tests.

## Quick Start

1. **Create a config file** (see `example_config.yaml`):

```yaml
name: "my_test"

input:
  mfotl: "path/to/formula.mfotl"
  signature: "path/to/signature.sig"
  log: "path/to/log.txt"
  functions: "path/to/functions.txt"

output:
  directory: "output"
  graph_html: "graph.html"
  save_json: false
  workflow_log: "workflow.log"
  enforcement_results: "results.txt"

visualization:
  enabled: true
  filter_polarity: false
  merge_strategy: "by_descendants"  # or "no_merge"

partition_execution:
  enabled: true
  timeout: 300  # seconds per partition
```

2. **Run the workflow**:

```bash
python run_workflow.py my_config.yaml
```

## What It Does

1. Generates JSON from MFOTL formula
2. Creates interactive dependency graph visualization
3. Generates partition MFOTL files based on dependencies
4. Runs enfguard on each partition (optional)
5. Compares timing against original formula
6. Saves all outputs to one directory

## Output Structure

```
output_directory/
├── graph.html              # Interactive visualization
├── workflow.log            # Execution log (latest run only)
├── enforcement_results.txt # Detailed timing results
└── mfotl/                  # Generated partition files
    ├── formula_partition_1.mfotl
    ├── formula_partition_2.mfotl
    └── ...
```

## Configuration Options

### Required
- `input.mfotl` - MFOTL formula file
- `input.signature` - Signature file
- `output.directory` - Output directory
- `visualization.merge_strategy` - `"by_descendants"` or `"no_merge"`

### Optional
- `input.log`, `input.functions` - Required only if `partition_execution.enabled: true`
- `output.save_json` - Keep intermediate JSON (default: true)
- `output.workflow_log` - Workflow execution log name
- `output.enforcement_results` - Enforcement results file name
- `visualization.filter_polarity` - Filter polarity edges (default: false)
- `partition_execution.timeout` - Timeout in seconds per partition

## Common Use Cases

**Just generate partitions** (no enforcement):
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
  partition_dir: "existing_output/mfotl"
```

## Dependencies

- Python 3.7+
- PyYAML: `pip install pyyaml`
- PyVis, NetworkX, Jinja2 (for visualization)

