# Running All Enfflash Configs

This directory contains scripts to run all enfflash workflow configurations automatically.

## Available Scripts

### 1. Bash Script (Simple)
```bash
./run_all_enfflash_configs.sh
```

**Features:**
- Runs all `minitwit_enfflash*.yaml` configs sequentially
- Colored output for easy monitoring
- Creates timestamped batch log
- Exits on first failure

### 2. Python Script (Advanced)
```bash
python3 run_all_enfflash_configs.py [OPTIONS] [CONFIG_FILES...]
```

**Options:**
- `configs` (positional) - Specific config files to run in order
- `--config-list FILE` - Path to text file listing configs (one per line)
- `--pattern PATTERN` - Glob pattern for config files (default: `minitwit_enfflash*.yaml`)
- `--configs-dir DIR` - Directory containing config files (default: `./configs`)
- `--continue-on-error` - Continue running even if a config fails
- `--dry-run` - Show which configs would be run without executing

**Examples:**
```bash
# Run all enfflash configs using pattern (default)
python3 run_all_enfflash_configs.py

# Run specific configs in a defined order
python3 run_all_enfflash_configs.py minitwit_enfflash_new_5.yaml minitwit_enfflash_new_10.yaml minitwit_enfflash_new_20.yaml

# Run configs listed in a file (see configs/example_run_order.txt)
python3 run_all_enfflash_configs.py --config-list configs/example_run_order.txt

# Quick test with just a few configs
python3 run_all_enfflash_configs.py --config-list configs/quick_test.txt

# Run with a custom pattern
python3 run_all_enfflash_configs.py --pattern "minitwit_enfflash_new_*.yaml"

# Continue even if some configs fail
python3 run_all_enfflash_configs.py --continue-on-error

# Dry run to see what would be executed
python3 run_all_enfflash_configs.py --dry-run

# Use custom config directory
python3 run_all_enfflash_configs.py --configs-dir /path/to/configs
```

**Config List File Format:**
Create a text file (e.g., `my_configs.txt`) with one config per line:
```
# Lines starting with # are comments
minitwit_enfflash_new_5.yaml
minitwit_enfflash_new_10.yaml
minitwit_enfflash_new_20.yaml
# Full paths also work:
# /full/path/to/config.yaml
```

## Output

Both scripts create:
- **Batch log**: `results/batch_run_<timestamp>.log` - Contains complete run history
- **Individual outputs**: `results/enfflash_<config_name>_<timestamp>/` - Per-config results

## Config Files Processed

The scripts automatically find and process configs matching the pattern:
- `minitwit_enfflash.yaml`
- `minitwit_enfflash_new.yaml`
- `minitwit_enfflash_new_5.yaml`
- `minitwit_enfflash_new_10.yaml`
- `minitwit_enfflash_new_15.yaml`
- `minitwit_enfflash_new_20.yaml`
- `minitwit_enfflash_new_25.yaml`
- `minitwit_enfflash_new_30.yaml`
- `minitwit_enfflash_new_40.yaml`
- `minitwit_enfflash_new_long_enfguard.yaml`

## Summary Output

At the end of execution, you'll see:
```
========================================
Batch Run Summary
========================================
End time: 2026-04-30 14:23:45
Total time: 45.3 minutes
Total configs: 10
Successful: 9
Failed: 1
Batch log: results/batch_run_20260430_142345.log
========================================
```

## Monitoring Progress

The scripts provide colored, real-time output:
- 🟦 **Blue**: Overall batch information
- 🟨 **Yellow**: Current config being processed  
- 🟢 **Green**: Success messages
- 🔴 **Red**: Failure messages

## Notes

- Each workflow has a 2-hour timeout (Python script only)
- Results are timestamped to avoid overwriting previous runs
- Use `--continue-on-error` for unattended batch processing
- Check the batch log file for complete execution history
