#!/usr/bin/env python3
"""
Workflow runner for partition-based enforcement testing.
Reads a YAML config file and executes visualization and/or partition enforcement.
"""

import argparse
import json
import os
import shutil
import sys
import subprocess
import time
import yaml
from datetime import datetime
from pathlib import Path

# CONFIGURATION CONSTANTS

# Default output filenames
DEFAULT_GRAPH_HTML = 'graph.html'
DEFAULT_WORKFLOW_LOG = 'workflow.log'
DEFAULT_ENFORCEMENT_RESULTS = 'enforcement_results.json'

# Directory names
DIR_VIZ = 'viz'
DIR_MFOTL = 'mfotl'
DIR_PARTITION_OUTPUTS = 'partition_outputs'
DIR_PLOTS = 'plots'
DIR_DIFF = 'diff'
DEFAULT_OUTPUT_BASE = 'tests/partition/results'

# File patterns and extensions
FILE_PATTERN_MFOTL = '*.mfotl'
FILE_PATTERN_DIFF = '*diff*.json'  # Matches both 'diff_*.json' and '*_diff.json'
FILE_EXT_JSON = '.json'
FILE_EXT_NORMALIZED = '_normalized.mfotl'
FILE_EXT_TMP = '.tmp'

# Plot filenames
PLOT_STEP_BY_STEP_TIMING = 'step_by_step_timing_plot.png'
PLOT_COMPLEXITY_VS_TIME = 'complexity_vs_time_plot.png'
PLOT_PARTITION_DIFFERENCES = 'partition_differences_plot.png'
PLOT_MULTI_LOG_MATCHING_STATUS = 'summary_matching_status.png'
PLOT_MULTI_LOG_SPEEDUP = 'summary_speedup.png'
PLOT_MULTI_LOG_COMPLEXITY = 'summary_complexity_vs_time.png'

# Timeouts (seconds)
TIMEOUT_PLOT_GENERATION = 30

# Logging
LOG_SEPARATOR_LENGTH = 80
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_SUCCESS = "SUCCESS"
LOG_LEVEL_WARNING = "WARNING"

# Subprocess settings
PYTHON_UNBUFFERED = '1'
LINE_BUFFER_SIZE = 1

# Mode strings
MODE_STEP_BY_STEP = "STEP-BY-STEP"
MODE_STANDARD = "STANDARD"


# =============================================================================
# CONFIGURATION AND LOGGING
# =============================================================================

class WorkflowLogger:
    """Simple logger that writes to both console and file."""
    
    def __init__(self, log_file=None):
        self.log_file = log_file
        self.start_time = time.time()
        
        # Clear log file at start (truncate previous runs)
        if self.log_file:
            with open(self.log_file, 'w') as f:
                pass  # Just truncate the file
    
    def log(self, message, level="INFO"):
        timestamp = time.time() - self.start_time
        log_line = f"[{timestamp:8.2f}s] [{level}] {message}"
        print(log_line, flush=True)  # Force flush for real-time output
        
        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(log_line + '\n')
    
    def section(self, title):
        separator = "=" * LOG_SEPARATOR_LENGTH
        self.log(separator)
        self.log(title)
        self.log(separator)


def load_config(config_file):
    """Load and validate configuration from YAML file."""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Validate required fields
    required_fields = ['name', 'input', 'output', 'visualization']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field in config: {field}")
    
    # construct output dir
    config['output']['directory'] = os.path.join(DEFAULT_OUTPUT_BASE, config['name'])
    
    # Process log configuration (support multiple logs or directory)
    log_files = []
    if 'logs' in config['input'] and config['input']['logs']:
        # Multiple logs specified explicitly (and not empty/None)
        log_files = config['input']['logs']
    elif 'log_directory' in config['input']:
        # Directory of log files
        log_dir = config['input']['log_directory']
        if os.path.isdir(log_dir):
            # Find all .log files in the directory
            log_files = sorted([
                os.path.join(log_dir, f) 
                for f in os.listdir(log_dir) 
                if f.endswith('.log')
            ])
            if not log_files:
                raise ValueError(f"No .log files found in directory: {log_dir}")
        else:
            raise ValueError(f"log_directory does not exist: {log_dir}")
    else:
        raise ValueError("Must specify either input.logs (list) or input.log_directory (directory path)")
    
    # Store processed log files
    config['_processed_log_files'] = log_files
    
    # Set defaults
    if 'partition_execution' not in config:
        config['partition_execution'] = {'enabled': False}
    
    if config['output'].get('save_json') is None:
        config['output']['save_json'] = True
    
    if config['output'].get('save_normalized_mfotl') is None:
        config['output']['save_normalized_mfotl'] = False
    
    # Set defaults for partition execution
    if config['partition_execution'].get('step_by_step') is None:
        config['partition_execution']['step_by_step'] = False
    
    if config['partition_execution'].get('repeat_runs') is None:
        config['partition_execution']['repeat_runs'] = 1
    
    # Auto-set partition directory if not specified
    if config['partition_execution'].get('enabled'):
        if config['partition_execution'].get('partition_dir') is None:
            config['partition_execution']['partition_dir'] = os.path.join(
                config['output']['directory'], DIR_MFOTL
            )
    
    return config


# =============================================================================
# FILE GENERATION FUNCTIONS
# =============================================================================

def generate_json(config, logger, workspace_root):
    """Generate JSON from MFOTL using enfguard."""
    logger.log("Generating JSON from MFOTL...")
    
    mfotl_file = config['input']['mfotl']
    sig_file = config['input']['signature']
    output_dir = config['output']['directory']
    
    # Make output directory absolute if it's relative
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine JSON output path (absolute)
    json_file = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(mfotl_file))[0] + FILE_EXT_JSON
    )
    
    # Build enfguard command
    enfguard_binary = os.path.join(workspace_root, 'enfguard')
    
    cmd = [
        enfguard_binary,
        '-sig', sig_file,
        '-formula', mfotl_file,
        '-print-normal-form',
        '-json',
        '-label'
    ]
    
    logger.log(f"Command: {' '.join(cmd)}")
    
    try:
        # Run command and capture output to save as JSON
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=workspace_root
        )
        
        # Save JSON to file
        with open(json_file, 'w') as f:
            f.write(result.stdout)
        
        logger.log(f"JSON saved to: {json_file}")
        return json_file
        
    except subprocess.CalledProcessError as e:
        logger.log(f"✗ JSON generation failed with exit code {e.returncode}", LOG_LEVEL_ERROR)
        if e.stderr:
            logger.log(f"stderr: {e.stderr}", LOG_LEVEL_ERROR)
        return None


def generate_normalized_mfotl(config, logger, workspace_root, script_dir):
    """Generate normalized MFOTL from original MFOTL using enfguard and pretty print it."""
    logger.log("Generating normalized MFOTL...")
    
    mfotl_file = config['input']['mfotl']
    sig_file = config['input']['signature']
    output_dir = config['output']['directory']
    
    # Make output directory absolute if it's relative
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine normalized MFOTL output path (absolute)
    normalized_file = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(mfotl_file))[0] + FILE_EXT_NORMALIZED
    )
    
    # Create temp file for raw enfguard output
    temp_file = normalized_file + FILE_EXT_TMP
    
    # Build enfguard command (same as JSON generation but without -json flag)
    enfguard_binary = os.path.join(workspace_root, 'enfguard')
    
    cmd = [
        enfguard_binary,
        '-sig', sig_file,
        '-formula', mfotl_file,
        '-print-normal-form',
        '-label'
    ]
    
    logger.log(f"Command: {' '.join(cmd)}")
    
    try:
        # Run command and capture output to save as normalized MFOTL
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=workspace_root
        )
        
        # Save raw normalized MFOTL to temp file
        with open(temp_file, 'w') as f:
            f.write(result.stdout)
        
        logger.log("Pretty-printing normalized MFOTL...")
        
        # Run pretty printer
        pretty_printer = os.path.join(script_dir, 'utils', 'pretty_print_normalized_mfotl.py')
        pretty_cmd = [sys.executable, pretty_printer, temp_file, normalized_file]
        
        pretty_result = subprocess.run(
            pretty_cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=workspace_root
        )
        
        # Clean up temp file
        os.remove(temp_file)
        
        logger.log(f"Normalized MFOTL saved to: {normalized_file}")
        return normalized_file
        
    except subprocess.CalledProcessError as e:
        logger.log(f"✗ Normalized MFOTL generation failed with exit code {e.returncode}", LOG_LEVEL_ERROR)
        if e.stderr:
            logger.log(f"stderr: {e.stderr}", LOG_LEVEL_ERROR)
        # Clean up temp file if it exists
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return None


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def run_visualization(config, logger, workspace_root, json_file):
    """Run visualize_graph.py to generate partitions and graph."""
    logger.log("Generating visualization and partitions...")
    
    mfotl_file = config['input']['mfotl']
    output_dir = config['output']['directory']
    
    # Make output directory absolute if it's relative
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    output_html = DEFAULT_GRAPH_HTML
    
    # Build command
    viz_script = os.path.join(workspace_root, DIR_VIZ, 'visualize_graph.py')
    
    cmd = [
        sys.executable,  # Use current Python interpreter
        viz_script,
        json_file,
        output_html,
        '--output-dir', output_dir,
        '--merge-strategy', config['visualization']['merge_strategy']
    ]
    
    if config['visualization'].get('filter_polarity'):
        cmd.append('--filter-polarity')
    
    if config['visualization'].get('max_merge_size') is not None:
        cmd.extend(['--max-merge-size', str(config['visualization']['max_merge_size'])])
    
    if config['input'].get('mfotl'):
        cmd.extend(['--mfotl', config['input']['mfotl']])
    
    logger.log(f"Command: {' '.join(cmd)}")
    logger.log("")  # Empty line before output
    
    try:
        # Run command with real-time output (line buffering)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=LINE_BUFFER_SIZE,  # Line buffering for real-time output
            cwd=workspace_root
        )
        
        # Stream output in real time
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.log(line)
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code == 0:
            logger.log("✓ Visualization completed successfully", LOG_LEVEL_SUCCESS)
            return True
        else:
            logger.log(f"✗ Visualization failed with exit code {return_code}", LOG_LEVEL_ERROR)
            return False
        
    except Exception as e:
        logger.log(f"✗ Visualization failed: {e}", LOG_LEVEL_ERROR)
        return False


# =============================================================================
# ENFORCEMENT EXECUTION
# =============================================================================

def run_partition_enforcement(config, logger, workspace_root, script_dir, log_file, log_output_subdir):
    """Run run_partition_enfguard.py on generated partitions for a specific log file.
    
    Args:
        config: Configuration dictionary
        logger: WorkflowLogger instance
        workspace_root: Root directory of workspace
        script_dir: Directory containing the script
        log_file: Path to the log file to use for enforcement
        log_output_subdir: Subdirectory name for this log's outputs (e.g., "log_minitwit_compliant")
    """
    mode_str = MODE_STEP_BY_STEP if config['partition_execution'].get('step_by_step') else MODE_STANDARD
    logger.log(f"Running enforcement on log: {os.path.basename(log_file)} ({mode_str} MODE)")
    
    partition_dir = config['partition_execution']['partition_dir']
    
    # Make partition directory absolute if it's relative
    if not os.path.isabs(partition_dir):
        partition_dir = os.path.join(workspace_root, partition_dir)
    
    if not os.path.exists(partition_dir):
        logger.log(f"✗ Partition directory not found: {partition_dir}", LOG_LEVEL_ERROR)
        return False
    
    # Count partition files
    partition_files = list(Path(partition_dir).glob(FILE_PATTERN_MFOTL))
    logger.log(f"Found {len(partition_files)} partition files")
    
    if not partition_files:
        logger.log("✗ No partition files found", LOG_LEVEL_ERROR)
        return False
    
    # Create output directory for this log's partition outputs and diffs
    output_dir = config['output']['directory']
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    log_output_dir = os.path.join(output_dir, log_output_subdir)
    partition_outputs_dir = os.path.join(log_output_dir, DIR_PARTITION_OUTPUTS)
    os.makedirs(partition_outputs_dir, exist_ok=True)
    logger.log(f"Output directory: {partition_outputs_dir}")
    
    # Build command
    runner_script = os.path.join(script_dir, 'utils', 'run_partition_enfguard.py')
    
    cmd = [
        sys.executable,
        runner_script,
        partition_dir,
        '-sig', config['input']['signature'],
        '-log', log_file,
        '-func', config['input']['functions'],
        '-o', partition_outputs_dir  # Add output directory for saving outputs and diffs
    ]
    
    # Always use input.mfotl as reference for timing comparison
    if config['input'].get('mfotl'):
        cmd.extend(['-ref', config['input']['mfotl']])
    
    if config['partition_execution'].get('timeout'):
        cmd.extend(['-t', str(config['partition_execution']['timeout'])])
    
    if config['partition_execution'].get('label'):
        cmd.append('-l')
    
    # Add step-by-step flag if enabled
    if config['partition_execution'].get('step_by_step'):
        cmd.append('-s')
    
    # Add repeat runs if specified
    if config['partition_execution'].get('repeat_runs'):
        cmd.extend(['-r', str(config['partition_execution']['repeat_runs'])])
    
    # Add JSON summary argument (always enabled with fixed filename in log subdirectory)
    enforcement_results_file = os.path.join(log_output_dir, DEFAULT_ENFORCEMENT_RESULTS)
    
    # Add json-summary argument
    cmd.extend(['-j', enforcement_results_file])
    
    logger.log(f"Command: {' '.join(cmd)}")
    logger.log("")  # Empty line before output
    
    try:
        # Set environment to disable Python output buffering
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = PYTHON_UNBUFFERED
        
        # Run command with real-time output (line buffering)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=LINE_BUFFER_SIZE,  # Line buffering for real-time output
            env=env,
            cwd=workspace_root
        )
        
        # Stream output in real time
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.log(line)
        
        # Wait for process to complete
        return_code = process.wait()
        
        # JSON summary is saved by run_partition_enfguard.py itself
        logger.log(f"Enforcement results summary saved to: {enforcement_results_file}")
        
        if return_code == 0:
            logger.log("✓ All partitions ran successfully", LOG_LEVEL_SUCCESS)
            return enforcement_results_file, log_output_dir
        else:
            logger.log(f"⚠ Some partitions failed or timed out (exit code {return_code})", LOG_LEVEL_WARNING)
            logger.log("See detailed results above for which partitions failed", LOG_LEVEL_WARNING)
            return enforcement_results_file, log_output_dir
        
    except Exception as e:
        logger.log(f"✗ Partition enforcement failed: {e}", LOG_LEVEL_ERROR)
        return None, None


# =============================================================================
# PLOTTING FUNCTIONS
# =============================================================================

def generate_step_by_step_plot(config, logger, workspace_root, script_dir, enforcement_results_file, plots_dir):
    """Generate timing plot for step-by-step execution results.
    
    Args:
        plots_dir: Directory where the plot should be saved
    """
    logger.log("Generating step-by-step timing plot...")
    
    if not os.path.exists(enforcement_results_file):
        logger.log(f"✗ Enforcement results file not found: {enforcement_results_file}", LOG_LEVEL_ERROR)
        return False
    
    # Use default plot filename in provided plots directory
    plot_filename = PLOT_STEP_BY_STEP_TIMING
    
    # Create plots subdirectory if it doesn't exist
    os.makedirs(plots_dir, exist_ok=True)
    
    plot_file = os.path.join(plots_dir, plot_filename)
    
    # Build command to run plotting script
    plot_script = os.path.join(script_dir, 'utils', 'plot_step_by_step_timing.py')
    
    if not os.path.exists(plot_script):
        logger.log(f"✗ Plotting script not found: {plot_script}", "ERROR")
        return False
    
    cmd = [
        sys.executable,
        plot_script,
        enforcement_results_file,
        '-o', plot_file
    ]
    
    logger.log(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            timeout=30
        )
        
        # Print script output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.log(line)
        
        if result.returncode == 0:
            logger.log(f"✓ Plot generated: {plot_file}", "SUCCESS")
            return True
        else:
            logger.log(f"✗ Plot generation failed with exit code {result.returncode}", "ERROR")
            if result.stderr:
                logger.log(f"Error output: {result.stderr}", "ERROR")
            return False
    
    except subprocess.TimeoutExpired:
        logger.log("✗ Plot generation timed out", "ERROR")
        return False
    except Exception as e:
        logger.log(f"✗ Plot generation failed: {e}", "ERROR")
        return False


def generate_complexity_plot(config, logger, workspace_root, script_dir, enforcement_results_file, partition_dir, plots_dir):
    """Generate complexity (rules/LETs) vs time plot for partition enforcement.
    
    Args:
        enforcement_results_file: Path to enforcement results JSON
        partition_dir: Directory containing partition MFOTL files
        plots_dir: Directory where the plot should be saved
    """
    logger.log("Generating complexity vs time plot...")
    
    if not os.path.exists(enforcement_results_file):
        logger.log(f"✗ Enforcement results file not found: {enforcement_results_file}", LOG_LEVEL_ERROR)
        return False
    
    if not os.path.exists(partition_dir):
        logger.log(f"✗ Partition directory not found: {partition_dir}", LOG_LEVEL_ERROR)
        return False
    
    # Use default plot filename in provided plots directory
    plot_filename = PLOT_COMPLEXITY_VS_TIME
    
    # Create plots subdirectory if it doesn't exist
    os.makedirs(plots_dir, exist_ok=True)
    
    plot_file = os.path.join(plots_dir, plot_filename)
    
    # Build command to run plotting script
    plot_script = os.path.join(script_dir, 'utils', 'plot_complexity_vs_time.py')
    
    if not os.path.exists(plot_script):
        logger.log(f"✗ Plotting script not found: {plot_script}", LOG_LEVEL_ERROR)
        return False
    
    cmd = [
        sys.executable,
        plot_script,
        enforcement_results_file,
        partition_dir,
        '-o', plot_file
    ]
    
    logger.log(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            timeout=TIMEOUT_PLOT_GENERATION
        )
        
        # Print script output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.log(line)
        
        if result.returncode == 0:
            logger.log(f"✓ Plot generated: {plot_file}", LOG_LEVEL_SUCCESS)
            return True
        else:
            logger.log(f"✗ Plot generation failed with exit code {result.returncode}", LOG_LEVEL_ERROR)
            if result.stderr:
                logger.log(f"Error output: {result.stderr}", LOG_LEVEL_ERROR)
            return False
    
    except subprocess.TimeoutExpired:
        logger.log("✗ Plot generation timed out", LOG_LEVEL_ERROR)
        return False
    except Exception as e:
        logger.log(f"✗ Plot generation failed: {e}", LOG_LEVEL_ERROR)
        return False


def generate_diff_statistics_plot(config, logger, workspace_root, script_dir, diff_dir, plots_dir):
    """Generate partition difference statistics plot from diff files.
    
    Args:
        diff_dir: Directory containing diff JSON files
        plots_dir: Directory where the plot should be saved
    """
    logger.log("Generating partition difference statistics plot...")
    
    if not os.path.exists(diff_dir):
        logger.log(f"✗ Diff directory not found: {diff_dir}", LOG_LEVEL_ERROR)
        return False
    
    # Check if there are any diff files
    diff_files = list(Path(diff_dir).glob(FILE_PATTERN_DIFF))
    if not diff_files:
        logger.log(f"✗ No diff files found in: {diff_dir}", LOG_LEVEL_ERROR)
        return False
    
    logger.log(f"Found {len(diff_files)} diff files")
    
    # Create plots subdirectory if it doesn't exist
    os.makedirs(plots_dir, exist_ok=True)
    
    plot_file = os.path.join(plots_dir, PLOT_PARTITION_DIFFERENCES)
    
    # Build command to run plotting script
    plot_script = os.path.join(script_dir, 'utils', 'plot_diff_stats.py')
    
    if not os.path.exists(plot_script):
        logger.log(f"✗ Plotting script not found: {plot_script}", LOG_LEVEL_ERROR)
        return False
    
    cmd = [
        sys.executable,
        plot_script,
        diff_dir
    ]
    
    logger.log(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            timeout=TIMEOUT_PLOT_GENERATION
        )
        
        # Print script output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.log(line)
        
        if result.returncode == 0:
            logger.log(f"✓ Plot generated: {plot_file}", LOG_LEVEL_SUCCESS)
            return True
        else:
            logger.log(f"✗ Plot generation failed with exit code {result.returncode}", LOG_LEVEL_ERROR)
            if result.stderr:
                logger.log(f"Error output: {result.stderr}", LOG_LEVEL_ERROR)
            return False
    
    except subprocess.TimeoutExpired:
        logger.log("✗ Plot generation timed out", LOG_LEVEL_ERROR)
        return False
    except Exception as e:
        logger.log(f"✗ Plot generation failed: {e}", LOG_LEVEL_ERROR)
        return False


def generate_multi_log_summary_plots(config, logger, workspace_root, script_dir, summary_file, output_dir):
    """Generate summary plots across all logs.
    
    Args:
        config: Configuration dictionary
        logger: WorkflowLogger instance
        workspace_root: Path to workspace root
        script_dir: Path to script directory
        summary_file: Path to multi_log_summary.json
        output_dir: Base output directory containing log subdirectories
        
    Returns:
        True if successful, False otherwise
    """
    logger.log("Generating multi-log summary plots...")
    
    if not os.path.exists(summary_file):
        logger.log(f"✗ Multi-log summary file not found: {summary_file}", LOG_LEVEL_ERROR)
        return False
    
    # Find the mfotl directory
    mfotl_dir = os.path.join(output_dir, DIR_MFOTL)
    if not os.path.exists(mfotl_dir):
        logger.log(f"✗ MFOTL directory not found: {mfotl_dir}", LOG_LEVEL_ERROR)
        return False
    
    # Build command to run plotting script
    plot_script = os.path.join(script_dir, 'utils', 'plot_multi_log_summary.py')
    
    if not os.path.exists(plot_script):
        logger.log(f"✗ Plotting script not found: {plot_script}", LOG_LEVEL_ERROR)
        return False
    
    # Output prefix for plots
    plot_prefix = os.path.join(output_dir, 'summary')
    
    cmd = [
        sys.executable,
        plot_script,
        summary_file,
        output_dir,
        mfotl_dir,
        '-o', plot_prefix
    ]
    
    logger.log(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            timeout=TIMEOUT_PLOT_GENERATION
        )
        
        # Print script output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.log(line)
        
        if result.returncode == 0:
            logger.log(f"✓ Multi-log summary plots generated:", LOG_LEVEL_SUCCESS)
            logger.log(f"  - {PLOT_MULTI_LOG_MATCHING_STATUS}")
            logger.log(f"  - {PLOT_MULTI_LOG_SPEEDUP}")
            logger.log(f"  - {PLOT_MULTI_LOG_COMPLEXITY}")
            return True
        else:
            logger.log(f"✗ Plot generation failed with exit code {result.returncode}", LOG_LEVEL_ERROR)
            if result.stderr:
                logger.log(f"Error output: {result.stderr}", LOG_LEVEL_ERROR)
            return False
    
    except subprocess.TimeoutExpired:
        logger.log("✗ Plot generation timed out", LOG_LEVEL_ERROR)
        return False
    except Exception as e:
        logger.log(f"✗ Plot generation failed: {e}", LOG_LEVEL_ERROR)
        return False


# =============================================================================
# SUMMARY AND REPORTING
# =============================================================================

def load_enforcement_summary(enforcement_results_file, logger):
    """Load high-level enforcement summary from results file, excluding partition details.
    
    Args:
        enforcement_results_file: Path to enforcement results JSON file
        logger: WorkflowLogger instance
        
    Returns:
        Dictionary with high-level summary, or None if loading fails
    """
    if not os.path.exists(enforcement_results_file):
        return None
    
    try:
        with open(enforcement_results_file, 'r') as f:
            enforcement_data = json.load(f)
            # Extract only high-level summary, exclude partition_details
            return {
                'total_partitions': enforcement_data.get('total_partitions'),
                'status_counts': enforcement_data.get('status_counts'),
                'output_comparison': enforcement_data.get('output_comparison'),
                'combined_output_comparison': enforcement_data.get('combined_output_comparison'),
                'timing': enforcement_data.get('timing'),
                'failed_partitions': enforcement_data.get('failed_partitions')
            }
    except Exception as e:
        logger.log(f"Warning: Failed to load enforcement results: {e}", LOG_LEVEL_WARNING)
        return None


# =============================================================================
# MAIN WORKFLOW ORCHESTRATOR
# =============================================================================

def run_workflow(config_file):
    """Execute the complete workflow based on config."""
    # Load configuration
    config = load_config(config_file)
    
    # Get workspace root (assumes script is in tests/partition/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Make output directory absolute if it's relative
    output_dir = config['output']['directory']
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    # Clear output directory if it already exists (start fresh)
    if os.path.exists(output_dir):
        print(f"Clearing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create output directory fresh
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup logger (always enabled with fixed filename)
    log_file = os.path.join(output_dir, DEFAULT_WORKFLOW_LOG)
    
    logger = WorkflowLogger(log_file)
    
    # Print workflow header
    logger.section(f"PARTITION WORKFLOW: {config['name']}")
    logger.log(f"Config file: {config_file}")
    logger.log(f"Timestamp: {datetime.now().isoformat()}")
    logger.log(f"Workspace: {workspace_root}")
    logger.log(f"Log file: {log_file}")
    
    success = True
    json_file = None
    
    # Step 1: Generate JSON and run visualization if enabled
    if config['visualization'].get('enabled'):
        logger.section("STEP 1: GENERATING VISUALIZATION AND PARTITIONS")
        
        # Step 1a: Generate JSON from MFOTL
        json_file = generate_json(config, logger, workspace_root)
        if not json_file:
            success = False
            logger.section("WORKFLOW FAILED")
            return 1
        
        # Step 1b: Generate visualization and partitions
        if not run_visualization(config, logger, workspace_root, json_file):
            success = False
            if not config['partition_execution'].get('enabled'):
                logger.section("WORKFLOW FAILED")
                return 1
        
        # Step 1c: Cleanup JSON if not needed
        if not config['output'].get('save_json') and os.path.exists(json_file):
            os.remove(json_file)
            logger.log(f"Removed intermediate JSON file")
    
    # Step 1.5: Generate normalized MFOTL if enabled
    if config['output'].get('save_normalized_mfotl'):
        normalized_file = generate_normalized_mfotl(config, logger, workspace_root, script_dir)
        if not normalized_file:
            logger.log("Warning: Failed to generate normalized MFOTL, continuing...", LOG_LEVEL_WARNING)
    else:
        logger.log("Visualization step skipped (disabled in config)")
    
    # Step 2: Run partition enforcement if enabled (iterate over all logs)
    log_results_summary = []
    if config['partition_execution'].get('enabled'):
        log_files = config['_processed_log_files']
        logger.section(f"STEP 2: RUNNING ENFORCEMENT ON PARTITIONS ({len(log_files)} log(s))")
        
        # Get partition directory (needed for plots)
        partition_dir = config['partition_execution']['partition_dir']
        if not os.path.isabs(partition_dir):
            partition_dir = os.path.join(workspace_root, partition_dir)
        
        for log_idx, log_file in enumerate(log_files, 1):
            # Create subdirectory name from log file basename (without extension)
            log_basename = os.path.splitext(os.path.basename(log_file))[0]
            log_output_subdir = f"log_{log_basename}"
            
            logger.log("")
            logger.log(f"[{log_idx}/{len(log_files)}] Processing log: {os.path.basename(log_file)}")
            logger.log(f"Output subdirectory: {log_output_subdir}")
            logger.log("="*LOG_SEPARATOR_LENGTH)
            
            # Run enforcement for this log
            enforcement_results_file, log_output_dir = run_partition_enforcement(
                config, logger, workspace_root, script_dir, 
                log_file, log_output_subdir
            )
            
            if not enforcement_results_file:
                logger.log(f"⚠ Enforcement failed for log: {os.path.basename(log_file)}", LOG_LEVEL_WARNING)
                success = False
                log_results_summary.append({
                    'log_file': os.path.basename(log_file),
                    'log_path': log_file,
                    'output_subdir': log_output_subdir,
                    'status': 'failed',
                    'enforcement_summary': None
                })
                continue
            
            # Load enforcement results summary (excluding partition details)
            enforcement_summary = load_enforcement_summary(enforcement_results_file, logger)
            
            log_results_summary.append({
                'log_file': os.path.basename(log_file),
                'log_path': log_file,
                'output_subdir': log_output_subdir,
                'status': 'success',
                'enforcement_summary': enforcement_summary
            })
            
            # Get subdirectories for this log
            plots_dir = os.path.join(log_output_dir, DIR_PLOTS)
            diff_dir = os.path.join(log_output_dir, DIR_PARTITION_OUTPUTS, DIR_DIFF)
            
            # Generate step-by-step timing plot if enabled and results exist
            if (config['partition_execution'].get('step_by_step') and 
                os.path.exists(enforcement_results_file)):
                if not generate_step_by_step_plot(config, logger, workspace_root, script_dir, 
                                                  enforcement_results_file, plots_dir):
                    logger.log("Warning: Failed to generate timing plot, continuing...", LOG_LEVEL_WARNING)
            
            # Generate complexity vs time plot
            if os.path.exists(enforcement_results_file):
                if not generate_complexity_plot(config, logger, workspace_root, script_dir, 
                                               enforcement_results_file, partition_dir, plots_dir):
                    logger.log("Warning: Failed to generate complexity plot, continuing...", LOG_LEVEL_WARNING)
            
            # Generate partition difference statistics plot
            if os.path.exists(diff_dir):
                if not generate_diff_statistics_plot(config, logger, workspace_root, script_dir, 
                                                     diff_dir, plots_dir):
                    logger.log("Warning: Failed to generate diff statistics plot, continuing...", LOG_LEVEL_WARNING)
            
            logger.log(f"✓ Completed processing log: {os.path.basename(log_file)}")
        
        # Save multi-log summary if multiple logs were processed
        if len(log_files) > 1:
            logger.log("")
            logger.log("Generating multi-log summary...")
            summary_file = os.path.join(output_dir, "multi_log_summary.json")
            
            summary = {
                'workflow_name': config['name'],
                'timestamp': datetime.now().isoformat(),
                'total_logs': len(log_files),
                'successful_logs': sum(1 for r in log_results_summary if r['status'] == 'success'),
                'failed_logs': sum(1 for r in log_results_summary if r['status'] == 'failed'),
                'log_results': log_results_summary
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.log(f"Multi-log summary saved to: {summary_file}")
            
            # Generate multi-log summary plots
            if not generate_multi_log_summary_plots(config, logger, workspace_root, script_dir, 
                                                     summary_file, output_dir):
                logger.log("Warning: Failed to generate multi-log summary plots, continuing...", LOG_LEVEL_WARNING)
    else:
        logger.log("Partition enforcement step skipped (disabled in config)")
    
    # Final summary
    logger.section("WORKFLOW COMPLETE")
    
    # List all output files (use absolute path)
    logger.log("\nGenerated files in output directory:")
    output_dir = config['output']['directory']
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    if os.path.exists(output_dir):
        for root, dirs, files in os.walk(output_dir):
            level = root.replace(output_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            logger.log(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in sorted(files):
                logger.log(f"{subindent}{file}")
    
    if success:
        logger.log("\n✓ All enabled steps completed successfully", LOG_LEVEL_SUCCESS)
        return 0
    else:
        logger.log("\n✗ Some steps failed (see log above)", LOG_LEVEL_ERROR)
        return 1


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Run partition workflow from config file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python run_workflow.py example_config.yaml
        """
    )
    parser.add_argument('config', help='Path to YAML configuration file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)
    
    sys.exit(run_workflow(args.config))
