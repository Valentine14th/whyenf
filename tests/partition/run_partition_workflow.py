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
    logger.section("STEP 2: RUNNING ENFORCEMENT ON PARTITIONS")
    
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
    runner_script = os.path.join(script_dir, 'run_partition_enfguard.py')
    
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
    
    logger.log(f"Command: {' '.join(cmd)}")
    logger.log("")  # Empty line before output
    
    # Prepare output file for enforcement results
    enforcement_results_file = None
    output_lines = []
    
    if config['output'].get('enforcement_results'):
        enforcement_results_file = config['output'].get('enforcement_results')
        # Make absolute if relative
        if not os.path.isabs(enforcement_results_file):
            output_dir = config['output']['directory']
            if not os.path.isabs(output_dir):
                output_dir = os.path.join(workspace_root, output_dir)
            enforcement_results_file = os.path.join(output_dir, enforcement_results_file)
    
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
        
        # Stream output in real time and capture for file
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.log(line)
                output_lines.append(line)
        
        # Wait for process to complete
        return_code = process.wait()
        
        # Save detailed enforcement results to separate file
        if enforcement_results_file and output_lines:
            with open(enforcement_results_file, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write("PARTITION ENFORCEMENT RESULTS\n")
                f.write("=" * 80 + "\n\n")
                f.write('\n'.join(output_lines))
            logger.log(f"Detailed results saved to: {enforcement_results_file}")
        
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
    else:
        logger.log("Visualization step skipped (disabled in config)")
    
    # Step 2: Run partition enforcement if enabled
    if config['partition_execution'].get('enabled'):
        if not run_partition_enforcement(config, logger, workspace_root, script_dir):
            success = False
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
