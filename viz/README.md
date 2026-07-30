# viz

Interactive graph visualizer for WhyEnf causality rules. Takes a formula JSON produced by Enfguard and generates an interactive HTML graph showing rule dependencies, SCCs, and partition assignments.

## What it does

- Parses the `lets` and `instrs` fields from the formula JSON
- Builds a directed dependency graph of causality rules (CauByCau / CauBySup edges)
- Computes SCCs and groups rules into partitions using a configurable merge strategy
- Outputs a self-contained HTML file with a PyVis graph and a sidebar for filtering, highlighting, and inspecting partitions
- Optionally writes per-partition `.mfotl` (and `.sig`) files for independent monitoring

## Generating the input JSON

The input JSON is produced by the `enfguard` binary:

```bash
enfguard -sig <formula.sig> -formula <formula.mfotl> -print-normal-form -json -label > formula.json
```

## How to run

```bash
python visualize_graph.py <formula.json> <output.html> \
    --merge-strategy <by_descendants|no_merge> \
    [--output-dir partition_output] \
    [--mfotl <formula.mfotl>] \
    [--sig <formula.sig>] \
    [--filter-polarity] \
    [--max-merge-size N] \
    [--keep-single-rule-components-separate]
```

**Required arguments:**

| Argument | Description |
|---|---|
| `input` | Path to the formula JSON file |
| `output` | Basename of the output HTML file |
| `--merge-strategy` | `by_descendants` — merge partitions sharing the same descendants; `no_merge` — keep all separate |

**Example:**

```bash
python visualize_graph.py ../formula.json graph.html \
    --merge-strategy by_descendants \
    --mfotl ../formula.mfotl \
    --sig ../formula.sig \
    --output-dir out/
```

## Outputs

All files are written to `--output-dir` (default: `partition_output/`):

| File | Description |
|---|---|
| `<output>.html` | Interactive graph; open in a browser |
| `<base>_partition_N.mfotl` | Minimal MFOTL file for partition N (if `--mfotl` given) |
| `<base>_partition_N.sig` | Matching minimal sig for partition N (if `--sig` given) |
