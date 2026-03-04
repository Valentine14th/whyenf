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
        separator = "=" * 80
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
    
    # Auto-set partition directory if not specified
    if config['partition_execution'].get('enabled'):
        if config['partition_execution'].get('partition_dir') is None:
            config['partition_execution']['partition_dir'] = os.path.join(
                config['output']['directory'], 'mfotl'
            )
    
    return config


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
        os.path.splitext(os.path.basename(mfotl_file))[0] + '.json'
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
        logger.log(f"✗ JSON generation failed with exit code {e.returncode}", "ERROR")
        if e.stderr:
            logger.log(f"stderr: {e.stderr}", "ERROR")
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
        os.path.splitext(os.path.basename(mfotl_file))[0] + '_normalized.mfotl'
    )
    
    # Create temp file for raw enfguard output
    temp_file = normalized_file + '.tmp'
    
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
        logger.log(f"✗ Normalized MFOTL generation failed with exit code {e.returncode}", "ERROR")
        if e.stderr:
            logger.log(f"stderr: {e.stderr}", "ERROR")
        # Clean up temp file if it exists
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return None


def run_visualization(config, logger, workspace_root, json_file):
    """Run visualize_graph.py to generate partitions and graph."""
    logger.log("Generating visualization and partitions...")
    
    mfotl_file = config['input']['mfotl']
    output_dir = config['output']['directory']
    
    # Make output directory absolute if it's relative
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    output_html = config['output']['graph_html']
    
    # Build command
    viz_script = os.path.join(workspace_root, 'viz', 'visualize_graph.py')
    
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
            bufsize=1,  # Line buffering for real-time output
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
            logger.log("✓ Visualization completed successfully", "SUCCESS")
            return True
        else:
            logger.log(f"✗ Visualization failed with exit code {return_code}", "ERROR")
            return False
        
    except Exception as e:
        logger.log(f"✗ Visualization failed: {e}", "ERROR")
        return False


def run_partition_enforcement(config, logger, workspace_root, script_dir):
    """Run run_partition_enfguard.py on generated partitions."""
    mode_str = "STEP-BY-STEP" if config['partition_execution'].get('step_by_step') else "STANDARD"
    logger.section(f"STEP 2: RUNNING ENFORCEMENT ON PARTITIONS ({mode_str} MODE)")
    
    partition_dir = config['partition_execution']['partition_dir']
    
    # Make partition directory absolute if it's relative
    if not os.path.isabs(partition_dir):
        partition_dir = os.path.join(workspace_root, partition_dir)
    
    if not os.path.exists(partition_dir):
        logger.log(f"✗ Partition directory not found: {partition_dir}", "ERROR")
        return False
    
    # Count partition files
    partition_files = list(Path(partition_dir).glob("*.mfotl"))
    logger.log(f"Found {len(partition_files)} partition files")
    
    if not partition_files:
        logger.log("✗ No partition files found", "ERROR")
        return False
    
    # Create output directory for partition outputs and diffs
    output_dir = config['output']['directory']
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    partition_outputs_dir = os.path.join(output_dir, 'partition_outputs')
    os.makedirs(partition_outputs_dir, exist_ok=True)
    logger.log(f"Output directory: {partition_outputs_dir}")
    
    # Build command
    runner_script = os.path.join(script_dir, 'utils', 'run_partition_enfguard.py')
    
    cmd = [
        sys.executable,
        runner_script,
        partition_dir,
        '-sig', config['input']['signature'],
        '-log', config['input']['log'],
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
    
    # Add JSON summary argument if enforcement_results specified
    enforcement_results_file = None
    if config['output'].get('enforcement_results'):
        enforcement_results_file = config['output']['enforcement_results']
        # Make absolute if relative
        if not os.path.isabs(enforcement_results_file):
            output_dir = config['output']['directory']
            if not os.path.isabs(output_dir):
                output_dir = os.path.join(workspace_root, output_dir)
            enforcement_results_file = os.path.join(output_dir, enforcement_results_file)
        
        # Add json-summary argument
        cmd.extend(['-j', enforcement_results_file])
    
    logger.log(f"Command: {' '.join(cmd)}")
    logger.log("")  # Empty line before output
    
    try:
        # Set environment to disable Python output buffering
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        # Run command with real-time output (line buffering)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffering for real-time output
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
        if enforcement_results_file:
            logger.log(f"Enforcement results summary saved to: {enforcement_results_file}")
        
        if return_code == 0:
            logger.log("✓ All partitions ran successfully", "SUCCESS")
            return True
        else:
            logger.log(f"✗ Some partitions failed or timed out (exit code {return_code})", "ERROR")
            logger.log("See detailed results above for which partitions failed", "ERROR")
            return False
        
    except Exception as e:
        logger.log(f"✗ Partition enforcement failed: {e}", "ERROR")
        return False


def generate_step_by_step_plot(config, logger, workspace_root, script_dir, enforcement_results_file):
    """Generate timing plot for step-by-step execution results."""
    logger.section("STEP 3: GENERATING STEP-BY-STEP TIMING PLOT")
    
    if not os.path.exists(enforcement_results_file):
        logger.log(f"✗ Enforcement results file not found: {enforcement_results_file}", "ERROR")
        return False
    
    # Use default plot filename in plots subdirectory
    plot_filename = 'step_by_step_timing_plot.png'
    
    # Make absolute path
    output_dir = config['output']['directory']
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    # Create plots subdirectory
    plots_dir = os.path.join(output_dir, 'plots')
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


def generate_complexity_plot(config, logger, workspace_root, script_dir, enforcement_results_file):
    """Generate complexity (rules/LETs) vs time plot for partition enforcement."""
    logger.section("STEP 4: GENERATING COMPLEXITY VS TIME PLOT")
    
    if not os.path.exists(enforcement_results_file):
        logger.log(f"✗ Enforcement results file not found: {enforcement_results_file}", "ERROR")
        return False
    
    # Determine partition directory
    partition_dir = config['partition_execution'].get('partition_dir')
    if not partition_dir:
        # Use default: output_dir/mfotl
        output_dir = config['output']['directory']
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(workspace_root, output_dir)
        partition_dir = os.path.join(output_dir, 'mfotl')
    elif not os.path.isabs(partition_dir):
        partition_dir = os.path.join(workspace_root, partition_dir)
    
    if not os.path.exists(partition_dir):
        logger.log(f"✗ Partition directory not found: {partition_dir}", "ERROR")
        return False
    
    # Use default plot filename in plots subdirectory
    plot_filename = 'complexity_vs_time_plot.png'
    
    # Make absolute path
    output_dir = config['output']['directory']
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    # Create plots subdirectory
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    plot_file = os.path.join(plots_dir, plot_filename)
    
    # Build command to run plotting script
    plot_script = os.path.join(script_dir, 'utils', 'plot_complexity_vs_time.py')
    
    if not os.path.exists(plot_script):
        logger.log(f"✗ Plotting script not found: {plot_script}", "ERROR")
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


def generate_diff_statistics_plot(config, logger, workspace_root, script_dir):
    """Generate partition difference statistics plot from diff files."""
    logger.section("STEP 5: GENERATING PARTITION DIFFERENCE STATISTICS PLOT")
    
    # Determine diff directory
    output_dir = config['output']['directory']
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    
    diff_dir = os.path.join(output_dir, 'partition_outputs', 'diff')
    
    if not os.path.exists(diff_dir):
        logger.log(f"✗ Diff directory not found: {diff_dir}", "ERROR")
        return False
    
    # Check if there are any diff files
    diff_files = list(Path(diff_dir).glob('*_diff.json'))
    if not diff_files:
        logger.log(f"✗ No diff files found in: {diff_dir}", "ERROR")
        return False
    
    logger.log(f"Found {len(diff_files)} diff files")
    
    # Create plots subdirectory
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    plot_file = os.path.join(plots_dir, 'partition_differences_plot.png')
    
    # Build command to run plotting script
    plot_script = os.path.join(script_dir, 'utils', 'plot_diff_stats.py')
    
    if not os.path.exists(plot_script):
        logger.log(f"✗ Plotting script not found: {plot_script}", "ERROR")
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
    
    # Setup logger
    log_file = None
    if config['output'].get('workflow_log'):
        log_file = os.path.join(output_dir, config['output']['workflow_log'])
    
    logger = WorkflowLogger(log_file)
    
    # Print workflow header
    logger.section(f"PARTITION WORKFLOW: {config['name']}")
    logger.log(f"Config file: {config_file}")
    logger.log(f"Timestamp: {datetime.now().isoformat()}")
    logger.log(f"Workspace: {workspace_root}")
    
    if log_file:
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
            logger.log("Warning: Failed to generate normalized MFOTL, continuing...", "WARNING")
    else:
        logger.log("Visualization step skipped (disabled in config)")
    
    # Step 2: Run partition enforcement if enabled
    enforcement_results_file = None
    if config['partition_execution'].get('enabled'):
        if not run_partition_enforcement(config, logger, workspace_root, script_dir):
            success = False
        else:
            # Get enforcement results file path for plotting
            if config['output'].get('enforcement_results'):
                enforcement_results_file = config['output']['enforcement_results']
                if not os.path.isabs(enforcement_results_file):
                    output_dir_abs = config['output']['directory']
                    if not os.path.isabs(output_dir_abs):
                        output_dir_abs = os.path.join(workspace_root, output_dir_abs)
                    enforcement_results_file = os.path.join(output_dir_abs, enforcement_results_file)
    else:
        logger.log("Partition enforcement step skipped (disabled in config)")
    
    # Step 3: Generate step-by-step timing plot if enabled and results exist
    if (config['partition_execution'].get('enabled') and 
        config['partition_execution'].get('step_by_step') and 
        enforcement_results_file and 
        os.path.exists(enforcement_results_file)):
        if not generate_step_by_step_plot(config, logger, workspace_root, script_dir, enforcement_results_file):
            logger.log("Warning: Failed to generate timing plot, continuing...", "WARNING")
    
    # Step 4: Generate complexity vs time plot if enforcement ran
    if (config['partition_execution'].get('enabled') and 
        enforcement_results_file and 
        os.path.exists(enforcement_results_file)):
        if not generate_complexity_plot(config, logger, workspace_root, script_dir, enforcement_results_file):
            logger.log("Warning: Failed to generate complexity plot, continuing...", "WARNING")
    
    # Step 5: Generate partition difference statistics plot if enforcement ran
    if config['partition_execution'].get('enabled'):
        if not generate_diff_statistics_plot(config, logger, workspace_root, script_dir):
            logger.log("Warning: Failed to generate diff statistics plot, continuing...", "WARNING")
    
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
        logger.log("\n✓ All enabled steps completed successfully", "SUCCESS")
        return 0
    else:
        logger.log("\n✗ Some steps failed (see log above)", "ERROR")
        return 1


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
