#!/usr/bin/env python3
"""
Run enfguard on all partition MFOTL files in a directory.
"""

import os
import sys
import argparse
import json
import subprocess
import time
import difflib
import shutil
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import specialized enforcer diff module
try:
    from enforcer_diff import (
        compare_enforcer_outputs, 
        compare_blocks_json,
        save_comparison_report,
        save_comparison_json,
        parse_enforcer_output,
        combine_blocks_by_timepoint,
        blocks_to_json_file,
        load_blocks_from_json
    )
    ENFORCER_DIFF_AVAILABLE = True
except ImportError:
    ENFORCER_DIFF_AVAILABLE = False
    print("Warning: enforcer_diff module not available, will use basic diff")

# Import step-by-step executor module
try:
    from step_by_step_executor import (
        run_enfguard_step_by_step
    )
    STEP_BY_STEP_AVAILABLE = True
except ImportError:
    STEP_BY_STEP_AVAILABLE = False
    print("Warning: step_by_step_executor module not available, step-by-step mode disabled")


# =============================================================================
# UTILITY AND HELPER FUNCTIONS
# =============================================================================

def calculate_time_stats(time_runs: List[float]) -> Dict:
    """
    Calculate timing statistics from a list of execution times.
    
    Args:
        time_runs: List of execution times in seconds
        
    Returns:
        Dictionary with mean, std, min, max, and runs
    """
    if not time_runs:
        return {
            'mean': 0.0,
            'std': 0.0,
            'min': 0.0,
            'max': 0.0,
            'runs': []
        }
    
    if len(time_runs) == 1:
        return {
            'mean': time_runs[0],
            'std': 0.0,
            'min': time_runs[0],
            'max': time_runs[0],
            'runs': time_runs
        }
    
    return {
        'mean': float(np.mean(time_runs)),
        'std': float(np.std(time_runs)),
        'min': float(np.min(time_runs)),
        'max': float(np.max(time_runs)),
        'runs': time_runs
    }


def print_timing_result(
    name: str,
    status: str,
    time_stats: Dict,
    repeat_runs: int,
    is_reference: bool = False
) -> None:
    """
    Print execution timing result in a consistent format.
    
    Args:
        name: Name of the partition or "reference"
        status: Status string (e.g., "✓ SUCCESS", "⏱ TIMEOUT")
        time_stats: Time statistics dictionary
        repeat_runs: Number of repeat runs
        is_reference: Whether this is a reference execution
    """
    prefix = "" if is_reference else f"[{name}] "
    
    if repeat_runs > 1:
        print(f"{prefix}{status} - Mean time: {time_stats['mean']:.3f}s (±{time_stats['std']:.3f}s), "
              f"Min: {time_stats['min']:.3f}s, Max: {time_stats['max']:.3f}s")
    else:
        print(f"{prefix}{status} - Time: {time_stats['mean']:.2f}s")


def get_partition_id(partition_name: str) -> str:
    """
    Extract partition identifier from partition filename.
    E.g., 'mfotl_1106.mfotl' -> '1106'
    
    Args:
        partition_name: Name of partition file
        
    Returns:
        Partition identifier string
    """
    # Remove extension
    base_name = os.path.splitext(partition_name)[0]
    # Extract number part (assumes format like 'mfotl_1106')
    parts = base_name.split('_')
    if len(parts) > 1:
        return parts[-1]  # Return the last part after underscore
    return base_name  # Fallback to full name if no underscore


def create_result_dict(
    partition_name: str,
    status: str,
    exit_code: int,
    time_stats: Dict,
    output: Optional[str] = None,
    output_matches: Optional[bool] = None,
    match_percentage: Optional[float] = None,
    step_by_step_timing: Optional[Dict] = None,
    blocks_json: Optional[str] = None
) -> Dict:
    """
    Create a standardized result dictionary.
    
    Args:
        partition_name: Name of the partition file
        status: Status string
        exit_code: Process exit code
        time_stats: Time statistics dictionary
        output: Optional stdout output
        output_matches: Optional flag indicating if output matches reference
        match_percentage: Optional match percentage
        step_by_step_timing: Optional step-by-step timing data
        blocks_json: Optional path to JSON file containing parsed blocks
        
    Returns:
        Standardized result dictionary
    """
    return {
        'file': partition_name,
        'status': status,
        'exit_code': exit_code,
        'time_stats': time_stats,
        'output_matches': output_matches,
        'match_percentage': match_percentage,
        'output': output,
        'step_by_step_timing': step_by_step_timing,
        'blocks_json': blocks_json
    }


# =============================================================================
# CORE EXECUTION FUNCTIONS
# =============================================================================

def run_enfguard_command(
    mfotl_file: str,
    sig_file: str, 
    log_file: str, 
    func_file: str,
    label: bool = False,
    timeout: Optional[int] = None
) -> Tuple[int, str, str, float]:
    """
    Run enfguard on a single MFOTL file.
    
    Args:
        mfotl_file: Path to MFOTL formula file
        sig_file: Path to signature file
        log_file: Path to log file
        func_file: Path to functions file
        label: Enable label output
        timeout: Optional timeout in seconds
        
    Returns:
        Tuple of (exit_code, stdout, stderr, elapsed_time)
    """
    cmd = [
        "./enfguard",
        "-sig", sig_file,
        "-formula", mfotl_file,
        "-log", log_file,
        "-func", func_file
    ]
    
    if label:
        cmd.append("-label")
    
    if timeout:
        cmd = ["timeout", str(timeout)] + cmd
    
    start_time = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    elapsed_time = time.time() - start_time
    
    return result.returncode, result.stdout, result.stderr, elapsed_time


def handle_enfguard_failure(
    partition_name: str,
    exit_code: int,
    stderr: str,
    stdout: str,
    elapsed_time: float,
    output_subdir: Optional[str],
    is_first_run: bool
) -> Tuple[str, Dict]:
    """
    Handle enfguard command failure and create appropriate status.
    
    Args:
        partition_name: Name of the partition file
        exit_code: Process exit code
        stderr: Standard error output
        stdout: Standard output
        elapsed_time: Execution time
        output_subdir: Optional directory to save output
        is_first_run: Whether this is the first run
        
    Returns:
        Tuple of (status_string, time_stats_dict)
    """
    if exit_code == 124:
        status = "⏱ TIMEOUT"
        label = "timeout"
    else:
        status = f"✗ FAILED (exit code {exit_code})"
        label = "failure"
    
    print(f"[{partition_name}] {status} - Time: {elapsed_time:.2f}s")
    
    if exit_code != 124:
        print("Error output:")
        for line in stderr.split('\n')[:10]:
            print(f"  {line}")
    
    if is_first_run and output_subdir:
        save_partition_output(partition_name, stdout, output_subdir, label=label)
    
    return status, calculate_time_stats([elapsed_time])


# =============================================================================
# OUTPUT MANAGEMENT FUNCTIONS
# =============================================================================

def setup_output_directories(output_dir: str) -> Tuple[str, str]:
    """
    Create output directory structure.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Tuple of (output_subdir, diff_subdir)
    """
    os.makedirs(output_dir, exist_ok=True)
    output_subdir = os.path.join(output_dir, 'output')
    diff_subdir = os.path.join(output_dir, 'diff')
    os.makedirs(output_subdir, exist_ok=True)
    os.makedirs(diff_subdir, exist_ok=True)
    
    return output_subdir, diff_subdir


def save_partition_output(
    partition_name: str,
    output: str,
    output_subdir: str,
    label: str = "",
    skip_json: bool = False
) -> None:
    """
    Save partition output to file (both text and JSON format).
    
    Args:
        partition_name: Name of partition file
        output: Output string to save
        output_subdir: Directory to save output
        label: Optional label for the output file (e.g., "partial")
        skip_json: If True, skip JSON saving (used when JSON already saved with timing info)
    """
    if output_subdir and output:
        partition_id = get_partition_id(partition_name)
        
        # Save text output
        partition_output_file = os.path.join(
            output_subdir, 
            f"output_{partition_id}_{label}.txt" if label else f"output_{partition_id}.txt"
        )
        with open(partition_output_file, 'w') as f:
            f.write(output)
        
        # Parse and save blocks as JSON (unless skip_json is True)
        if ENFORCER_DIFF_AVAILABLE and not skip_json:
            blocks = parse_enforcer_output(output)
            # Create parsed_output subdirectory
            parsed_output_dir = os.path.join(output_subdir, "parsed_output")
            os.makedirs(parsed_output_dir, exist_ok=True)
            blocks_json_file = os.path.join(
                parsed_output_dir,
                f"blocks_{partition_id}_{label}.json" if label else f"blocks_{partition_id}.json"
            )
            blocks_to_json_file(blocks, blocks_json_file)
        
        # Print message based on whether this is partial output
        if label:
            print(f"  Saved {label} output to: {partition_output_file}")


# =============================================================================
# COMPARISON AND DIFF FUNCTIONS
# =============================================================================

def compare_and_save_diff(
    partition_name: str,
    partition_output: str,
    reference_output: str,
    diff_subdir: Optional[str]
) -> Tuple[bool, Optional[float]]:
    """
    Compare partition output with reference and save diff results.
    
    Args:
        partition_name: Name of partition file
        partition_output: Partition output string
        reference_output: Reference output string
        diff_subdir: Directory to save diffs
        
    Returns:
        Tuple of (output_matches, match_percentage)
    """
    # Compare outputs using enforcer_diff
    comparison = compare_enforcer_outputs(
        reference_output, 
        partition_output, 
        partition_name
    )
    match_percentage = comparison['summary']['match_percentage']
    output_matches = (
        comparison['summary']['differing_blocks'] == 0 and 
        len(comparison['missing_in_partition']) == 0 and
        len(comparison['extra_in_partition']) == 0
    )
    
    # Save diff report for all partitions (even when outputs match)
    if diff_subdir:
        partition_id = get_partition_id(partition_name)
        diff_file = os.path.join(
            diff_subdir,
            f"diff_{partition_id}.json"
        )
        save_comparison_json(comparison, diff_file)
    
    return output_matches, match_percentage


# =============================================================================
# STEP-BY-STEP TIMING FUNCTIONS
# =============================================================================

def aggregate_step_by_step_timing(step_by_step_runs: List[Dict]) -> Dict:
    """
    Aggregate step-by-step timing data across multiple runs.
    
    Args:
        step_by_step_runs: List of step-by-step timing dictionaries from multiple runs
        
    Returns:
        Aggregated step-by-step timing with statistics
    """
    if not step_by_step_runs:
        return None
    
    # Get number of steps (should be same across all runs)
    num_steps = step_by_step_runs[0]['total_steps']
    
    # Aggregate total times
    total_times = [run['total_time'] for run in step_by_step_runs]
    total_time_stats = {
        'mean': float(np.mean(total_times)),
        'std': float(np.std(total_times)),
        'min': float(np.min(total_times)),
        'max': float(np.max(total_times)),
        'runs': total_times
    }
    
    # Aggregate per-step timing
    aggregated_steps = []
    for step_idx in range(num_steps):
        # Collect timing for this step across all runs
        step_times = []
        cumulative_times = []
        timepoint = None
        timestamp = None
        block_type = None
        has_action = None
        
        for run in step_by_step_runs:
            if step_idx < len(run['steps']):
                step = run['steps'][step_idx]
                step_times.append(step['step_time'])
                cumulative_times.append(step['cumulative_time'])
                if timepoint is None:
                    timepoint = step['timepoint']
                    timestamp = step.get('timestamp')
                    block_type = step.get('block_type')
                    has_action = step.get('has_action')
        
        # Calculate statistics for this step
        if step_times:
            step_data = {
                'timepoint': timepoint,
                'timestamp': timestamp,
                'step_time_stats': {
                    'mean': float(np.mean(step_times)),
                    'std': float(np.std(step_times)),
                    'min': float(np.min(step_times)),
                    'max': float(np.max(step_times)),
                    'runs': step_times
                },
                'cumulative_time_stats': {
                    'mean': float(np.mean(cumulative_times)),
                    'std': float(np.std(cumulative_times)),
                    'min': float(np.min(cumulative_times)),
                    'max': float(np.max(cumulative_times)),
                    'runs': cumulative_times
                }
            }
            # Add block_type and has_action if available
            if block_type is not None:
                step_data['block_type'] = block_type
            if has_action is not None:
                step_data['has_action'] = has_action
            aggregated_steps.append(step_data)
    
    # Calculate average step time stats
    avg_step_times = [run.get('avg_step_time', 0.0) for run in step_by_step_runs]
    avg_step_time_stats = {
        'mean': float(np.mean(avg_step_times)),
        'std': float(np.std(avg_step_times)),
        'min': float(np.min(avg_step_times)),
        'max': float(np.max(avg_step_times)),
        'runs': avg_step_times
    }
    
    return {
        'status': step_by_step_runs[0]['status'],
        'total_steps': num_steps,
        'completed_steps': step_by_step_runs[0]['completed_steps'],
        'total_time_stats': total_time_stats,
        'steps': aggregated_steps,
        'avg_step_time_stats': avg_step_time_stats,
        'num_runs': len(step_by_step_runs)
    }


# =============================================================================
# EXECUTION HELPER FUNCTIONS
# =============================================================================

def execute_enfguard_runs(
    name: str,
    mfotl_file: str,
    sig_file: str,
    log_file: str,
    func_file: str,
    label: bool,
    timeout: Optional[int],
    output_subdir: Optional[str],
    step_by_step: bool,
    repeat_runs: int,
    is_reference: bool = False
) -> Tuple[Optional[str], Optional[Dict], Optional[Dict], List[Dict]]:
    """
    Execute enfguard in batch or step-by-step mode with multiple runs.
    
    Args:
        name: Display name for logging
        mfotl_file: Path to MFOTL file
        sig_file: Path to signature file
        log_file: Path to log file
        func_file: Path to functions file
        label: Enable label output
        timeout: Optional timeout in seconds
        output_subdir: Optional directory to save output
        step_by_step: Enable step-by-step mode
        repeat_runs: Number of repeat runs
        is_reference: Whether this is reference execution
        
    Returns:
        Tuple of (stdout, time_stats, aggregated_step_timing, step_by_step_runs)
    """
    # Validate step-by-step availability
    if step_by_step and not STEP_BY_STEP_AVAILABLE:
        print(f"[{name}] Warning: Step-by-step mode not available, using batch mode")
        step_by_step = False
    
    time_runs = []
    step_by_step_runs = []
    stdout_result = None
    
    # Execute runs
    for run_idx in range(repeat_runs):
        if step_by_step:
            # Step-by-step execution
            if run_idx == 0:
                print(f"[{name}] Step-by-step run {run_idx + 1}/{repeat_runs}")
            try:
                step_data = run_enfguard_step_by_step(
                    mfotl_file, sig_file, log_file, func_file,
                    label=label, timeout=timeout, output_dir=output_subdir
                )
                step_by_step_runs.append(step_data)
                time_runs.append(step_data.get('total_time', 0.0))
                
                if run_idx == 0:
                    stdout_result = step_data.get('stdout', '')
                    avg_time = step_data.get('avg_step_time', 0.0)
                    print(f"[{name}] {step_data['total_steps']} steps, avg {avg_time:.3f}s/step")
                elif repeat_runs > 1 and (run_idx + 1) % max(1, repeat_runs // 4) == 0:
                    print(f"[{name}] Progress: {run_idx + 1}/{repeat_runs} runs completed")
            except Exception as e:
                print(f"[{name}] Warning: Step-by-step run {run_idx + 1} failed: {e}")
        else:
            # Batch execution
            exit_code, stdout, stderr, elapsed_time = run_enfguard_command(
                mfotl_file, sig_file, log_file, func_file, label, timeout
            )
            
            if exit_code != 0:
                status, time_stats = handle_enfguard_failure(
                    name, exit_code, stderr, stdout, elapsed_time,
                    output_subdir, run_idx == 0
                )
                return None, None, None, []
            
            time_runs.append(elapsed_time)
            print(f"[{name}] Batch run {run_idx + 1}/{repeat_runs}: {elapsed_time:.3f}s")
            
            if run_idx == 0:
                stdout_result = stdout
    
    # Aggregate results
    if not time_runs:
        print(f"[{name}] ✗ ERROR: No timing data collected")
        return None, None, None, []
    
    time_stats = calculate_time_stats(time_runs)
    aggregated_step_timing = None
    
    if step_by_step_runs:
        aggregated_step_timing = aggregate_step_by_step_timing(step_by_step_runs)
        if repeat_runs > 1:
            avg_stats = aggregated_step_timing['avg_step_time_stats']
            print(f"[{name}] Aggregated: mean {avg_stats['mean']:.3f}s/step (±{avg_stats['std']:.3f}s)")
    
    return stdout_result, time_stats, aggregated_step_timing, step_by_step_runs


def save_execution_output(
    name: str,
    stdout: str,
    output_subdir: Optional[str],
    step_by_step_runs: List[Dict],
    is_reference: bool = False
) -> Optional[str]:
    """
    Save execution output and handle JSON files.
    
    Args:
        name: File name (e.g., "reference.mfotl" or partition name)
        stdout: Standard output to save
        output_subdir: Directory to save output
        step_by_step_runs: List of step-by-step run data (empty if batch mode)
        is_reference: Whether this is reference execution
        
    Returns:
        Path to blocks JSON file if created, else None
    """
    if not output_subdir:
        return None
    
    # Determine label and ID
    label = ""
    if is_reference:
        partition_id = "reference"
    else:
        partition_id = get_partition_id(name)
    
    # Save stdout (skip JSON if step-by-step already saved it)
    skip_json = len(step_by_step_runs) > 0
    save_partition_output(name, stdout, output_subdir, label=label, skip_json=skip_json)
    
    # Handle step-by-step JSON file renaming
    blocks_json_path = None
    if step_by_step_runs and step_by_step_runs[0].get('blocks_json'):
        src_json = step_by_step_runs[0]['blocks_json']
        parsed_output_dir = os.path.join(output_subdir, "parsed_output")
        dst_json = os.path.join(parsed_output_dir, f"blocks_{partition_id}.json")
        if os.path.exists(src_json):
            shutil.move(src_json, dst_json)
            blocks_json_path = dst_json
    
    return blocks_json_path


# =============================================================================
# MAIN EXECUTION FUNCTIONS
# =============================================================================

def run_reference_enfguard(
    reference_mfotl: str,
    sig_file: str,
    log_file: str,
    func_file: str,
    label: bool,
    timeout: Optional[int],
    output_subdir: Optional[str],
    step_by_step: bool = False,
    repeat_runs: int = 1
) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Run enfguard on reference MFOTL file.
    
    Args:
        reference_mfotl: Path to reference MFOTL file
        sig_file: Path to signature file
        log_file: Path to log file
        func_file: Path to functions file
        label: Enable label output
        timeout: Optional timeout in seconds
        output_subdir: Optional directory to save output
        step_by_step: Enable step-by-step execution mode
        repeat_runs: Number of times to run for timing measurements
        
    Returns:
        Tuple of (reference_output, reference_time_stats) or (None, None) if failed
    """
    print(f"RUNNING REFERENCE FILE: {reference_mfotl}")
    if repeat_runs > 1:
        print(f"  Repeat runs: {repeat_runs} (timing only)")
    
    try:
        # Execute runs
        stdout_result, time_stats, aggregated_step_timing, step_runs = execute_enfguard_runs(
            "reference", reference_mfotl, sig_file, log_file, func_file,
            label, timeout, output_subdir, step_by_step, repeat_runs, is_reference=True
        )
        
        if stdout_result is None:
            print()
            return None, None
        
        # Save output on first run
        save_execution_output("reference.mfotl", stdout_result, output_subdir, step_runs, is_reference=True)
        
        # Add step-by-step timing to time_stats if available
        if aggregated_step_timing:
            time_stats['step_by_step_timing'] = aggregated_step_timing
        
        print_timing_result("reference", "✓ SUCCESS", time_stats, repeat_runs, is_reference=True)
        print()
        return stdout_result, time_stats
                
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        print()
        return None, None


def run_partition_enfguard(
    mfotl_file: Path,
    sig_file: str,
    log_file: str,
    func_file: str,
    label: bool,
    timeout: Optional[int],
    reference_output: Optional[str],
    output_subdir: Optional[str],
    diff_subdir: Optional[str],
    step_by_step: bool = False,
    repeat_runs: int = 1
) -> Dict:
    """
    Run enfguard on a single partition file and compare with reference.
    
    Args:
        mfotl_file: Path to partition MFOTL file
        sig_file: Path to signature file
        log_file: Path to log file
        func_file: Path to functions file
        label: Enable label output
        timeout: Optional timeout in seconds
        reference_output: Optional reference output for comparison
        output_subdir: Optional directory to save outputs
        diff_subdir: Optional directory to save diffs
        step_by_step: If True, also collect per-timestamp timing information
        repeat_runs: Number of times to run for timing measurements
        
    Returns:
        Dictionary with result information including timing statistics
    """
    partition_name = mfotl_file.name
    print(f"\n[{partition_name}] Running enfguard...")
    
    try:
        # Execute runs
        stdout_result, time_stats, aggregated_step_timing, step_runs = execute_enfguard_runs(
            partition_name, str(mfotl_file), sig_file, log_file, func_file,
            label, timeout, output_subdir, step_by_step, repeat_runs
        )
        
        if stdout_result is None:
            return create_result_dict(
                partition_name, "ERROR", -1, calculate_time_stats([]), output=None
            )
        
        # Save output on first run
        blocks_json_path = save_execution_output(partition_name, stdout_result, output_subdir, step_runs)
        
        # Compare with reference if available
        output_matches = None
        match_percentage = None
        if reference_output is not None:
            output_matches, match_percentage = compare_and_save_diff(
                partition_name, stdout_result, reference_output, diff_subdir
            )
        
        # Print result
        status = "✓ SUCCESS"
        if repeat_runs > 1:
            print_timing_result(partition_name, status, time_stats, repeat_runs)
        elif reference_output is not None:
            match_str = "✓ MATCHES" if output_matches else "✗ DIFFERS"
            match_pct = f"{match_percentage:.2f}%" if match_percentage is not None else "unknown"
            print(f"[{partition_name}] {status} - Time: {time_stats['mean']:.2f}s - Output: {match_str} ({match_pct})")
            
            if diff_subdir:
                partition_id = get_partition_id(partition_name)
                print(f"  Detailed diff saved to: {os.path.join(diff_subdir, f'diff_{partition_id}.json')}")
        else:
            print(f"[{partition_name}] {status} - Time: {time_stats['mean']:.2f}s")
        
        return create_result_dict(
            partition_name, status, 0, time_stats,
            output=stdout_result,
            output_matches=output_matches,
            match_percentage=match_percentage,
            step_by_step_timing=aggregated_step_timing,
            blocks_json=blocks_json_path
        )
        
    except Exception as e:
        print(f"[{partition_name}] ✗ EXCEPTION: {e}")
        return create_result_dict(
            partition_name, 'EXCEPTION', -1, calculate_time_stats([])
        )


def combine_and_compare_partitions(
    results: List[Dict],
    reference_output: str,
    output_subdir: Optional[str],
    diff_subdir: Optional[str]
) -> Optional[Dict]:
    """
    Combine all partition outputs and compare to reference.
    
    Args:
        results: List of partition result dictionaries
        reference_output: Reference output string
        output_subdir: Directory to save combined output
        diff_subdir: Directory to save combined diff
        
    Returns:
        Dictionary with combined matching info, or None if comparison not available
    """
    if not ENFORCER_DIFF_AVAILABLE:
        return None
    
    # Collect all successful partition outputs
    successful_results = [r for r in results if r['output'] is not None]
    
    if not successful_results:
        return None
    
    print("\n" + "="*80)
    print("COMBINED PARTITION OUTPUT COMPARISON")
    print("="*80)
    
    # Parse all partition outputs into blocks
    # Use saved JSON files if available (from step-by-step execution)
    # Otherwise parse the output text
    all_blocks = []
    for result in successful_results:
        blocks_json_path = result.get('blocks_json')
        if blocks_json_path and os.path.exists(blocks_json_path):
            # Load blocks directly from JSON (already has correct timepoints)
            blocks = load_blocks_from_json(blocks_json_path)
        else:
            # Parse output (batch mode - assigns sequential timepoints)
            output = result['output']
            blocks = parse_enforcer_output(output)
        all_blocks.extend(blocks)
    
    # Combine blocks by timepoint (or timestamp if not available)
    combined_blocks = combine_blocks_by_timepoint(all_blocks)
    
    # Reconstruct combined output as text
    combined_output_lines = [block.raw_content for block in combined_blocks]
    combined_output = '\n'.join(combined_output_lines)
    
    # Save combined output (both text and JSON)
    if output_subdir:
        combined_output_file = os.path.join(output_subdir, "combined_partitions_output.txt")
        with open(combined_output_file, 'w') as f:
            f.write(combined_output)
        print(f"Combined output saved to: {combined_output_file}")
        
        # Save combined blocks as JSON
        parsed_output_dir = os.path.join(output_subdir, "parsed_output")
        os.makedirs(parsed_output_dir, exist_ok=True)
        combined_blocks_json_file = os.path.join(parsed_output_dir, "combined_partitions_blocks.json")
        blocks_to_json_file(combined_blocks, combined_blocks_json_file)
        print(f"Combined blocks JSON saved to: {combined_blocks_json_file}")
    
    # Compare combined output to reference
    # Load reference blocks from JSON if available (preserves step-by-step timepoints)
    # Otherwise parse the reference output
    reference_blocks_json = os.path.join(output_subdir, "parsed_output", "blocks_reference.json") if output_subdir else None
    if reference_blocks_json and os.path.exists(reference_blocks_json):
        ref_blocks = load_blocks_from_json(reference_blocks_json)
    else:
        ref_blocks = parse_enforcer_output(reference_output)
    
    combined_comparison = compare_blocks_json(
        ref_blocks,
        combined_blocks,
        "combined_partitions"
    )
    
    combined_match_pct = combined_comparison['summary']['match_percentage']
    combined_matches = (
        combined_comparison['summary']['differing_blocks'] == 0 and 
        len(combined_comparison['missing_in_partition']) == 0 and
        len(combined_comparison['extra_in_partition']) == 0
    )
    
    if combined_matches:
        print(f"✓ Combined partition output MATCHES reference (100.00%)")
    else:
        print(f"✗ Combined partition output DIFFERS from reference ({combined_match_pct:.2f}% matching)")
        print(f"  Matching blocks: {combined_comparison['summary']['matching_blocks']}/{combined_comparison['summary']['total_blocks']}")
        print(f"  Differing blocks: {combined_comparison['summary']['differing_blocks']}")
        print(f"  Missing in combined: {len(combined_comparison['missing_in_partition'])}")
        print(f"  Extra in combined: {len(combined_comparison['extra_in_partition'])}")
    
    # Save combined diff report (always, even when outputs match)
    if diff_subdir:
        combined_diff_file = os.path.join(diff_subdir, "combined_partitions_diff.json")
        save_comparison_json(combined_comparison, combined_diff_file)
        print(f"  Detailed diff saved to: {combined_diff_file}")
    
    # Return combined matching info
    return {
        'combined_matches': combined_matches,
        'combined_match_percentage': combined_match_pct,
        'matching_blocks': combined_comparison['summary']['matching_blocks'],
        'total_blocks': combined_comparison['summary']['total_blocks'],
        'differing_blocks': combined_comparison['summary']['differing_blocks'],
        'missing_blocks': len(combined_comparison['missing_in_partition']),
        'extra_blocks': len(combined_comparison['extra_in_partition'])
    }


# =============================================================================
# SUMMARY AND REPORTING FUNCTIONS
# =============================================================================

def print_summary(
    results: List[Dict],
    reference_output: Optional[str],
    reference_time: Optional[float]
) -> None:
    """
    Print summary of all partition runs.
    
    Args:
        results: List of partition result dictionaries
        reference_output: Optional reference output for comparison stats
        reference_time: Optional reference execution time
    """
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    # Count results by status
    success_count = sum(1 for r in results if r['exit_code'] == 0)
    timeout_count = sum(1 for r in results if r['exit_code'] == 124)
    failed_count = sum(1 for r in results if r['exit_code'] not in [0, 124])
    
    print(f"Total: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Timeout: {timeout_count}")
    print(f"Failed: {failed_count}")
    
    # Output comparison summary
    if reference_output is not None:
        matching_count = sum(1 for r in results if r.get('output_matches') is True)
        differing_count = sum(1 for r in results if r.get('output_matches') is False)
        
        print(f"\nOutput Comparison (vs reference):")
        print(f"  Matching: {matching_count}")
        print(f"  Differing: {differing_count}")
        
        if differing_count > 0:
            print(f"\nPartitions with differing outputs:")
            for r in results:
                if r.get('output_matches') is False:
                    match_pct = r.get('match_percentage')
                    if match_pct is not None:
                        print(f"  - {r['file']} ({match_pct:.2f}% matching)")
                    else:
                        print(f"  - {r['file']}")
    
    # Timing analysis
    successful_results = [r for r in results if r['exit_code'] == 0]
    if successful_results:
        # Use mean time from time_stats for calculations
        total_time = sum(r['time_stats']['mean'] for r in successful_results)
        avg_time = total_time / len(successful_results)
        min_time = min(r['time_stats']['mean'] for r in successful_results)
        max_time = max(r['time_stats']['mean'] for r in successful_results)
        fastest_partition = min(successful_results, key=lambda r: r['time_stats']['mean'])
        slowest_partition = max(successful_results, key=lambda r: r['time_stats']['mean'])
        
        print(f"\nTiming (successful runs only):")
        print(f"  Total time (sequential, mean): {total_time:.2f}s")
        print(f"  Average time (mean): {avg_time:.2f}s")
        print(f"  Min time (fastest): {min_time:.2f}s - {fastest_partition['file']}")
        print(f"  Max time (slowest): {max_time:.2f}s - {slowest_partition['file']}")
        
        if reference_time is not None:
            # reference_time is now a dict with stats
            ref_mean = reference_time['mean'] if isinstance(reference_time, dict) else reference_time
            speedup = ref_mean / max_time if max_time > 0 else 0
            print(f"\nComparison to reference (parallel execution):")
            print(f"  Reference time: {ref_mean:.2f}s")
            print(f"  Slowest partition: {max_time:.2f}s - {slowest_partition['file']}")
            if speedup >= 1:
                print(f"  Speedup: {speedup:.2f}x FASTER")
            else:
                print(f"  Slowdown: {1/speedup:.2f}x SLOWER")
    
    # Failed partitions details
    if failed_count > 0:
        print("\nFailed partitions:")
        for r in results:
            if r['exit_code'] not in [0, 124]:
                print(f"  - {r['file']} (exit code {r['exit_code']})")


def save_json_summary(
    results: List[Dict],
    reference_output: Optional[str],
    reference_time: Optional[float],
    json_file: str,
    combined_comparison: Optional[Dict] = None
) -> None:
    """
    Save comprehensive results summary as JSON.
    
    Args:
        results: List of partition result dictionaries
        reference_output: Optional reference output for comparison
        reference_time: Optional reference execution time
        json_file: Path to save JSON summary
        combined_comparison: Optional combined partition matching info
    """

    # Count results by status
    success_count = sum(1 for r in results if r['exit_code'] == 0)
    timeout_count = sum(1 for r in results if r['exit_code'] == 124)
    failed_count = sum(1 for r in results if r['exit_code'] not in [0, 124])
    
    # Output comparison summary
    matching_count = 0
    differing_count = 0
    differing_partitions = []
    
    if reference_output is not None:
        matching_count = sum(1 for r in results if r.get('output_matches') is True)
        differing_count = sum(1 for r in results if r.get('output_matches') is False)
        
        for r in results:
            if r.get('output_matches') is False:
                differing_partitions.append({
                    'file': r['file'],
                    'match_percentage': r.get('match_percentage')
                })
    
    # Timing analysis
    timing_info = None
    successful_results = [r for r in results if r['exit_code'] == 0]
    
    if successful_results:
        # Use mean time from time_stats for calculations
        total_time = sum(r['time_stats']['mean'] for r in successful_results)
        avg_time = total_time / len(successful_results)
        min_time = min(r['time_stats']['mean'] for r in successful_results)
        max_time = max(r['time_stats']['mean'] for r in successful_results)
        fastest_partition = min(successful_results, key=lambda r: r['time_stats']['mean'])
        slowest_partition = max(successful_results, key=lambda r: r['time_stats']['mean'])
        
        timing_info = {
            'total_sequential_time': total_time,
            'average_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'fastest_partition': {
                'file': fastest_partition['file'],
                'time': fastest_partition['time_stats']['mean'],
                'time_stats': fastest_partition['time_stats']
            },
            'slowest_partition': {
                'file': slowest_partition['file'],
                'time': slowest_partition['time_stats']['mean'],
                'time_stats': slowest_partition['time_stats']
            }
        }
        
        if reference_time is not None:
            # reference_time is now a dict with stats
            ref_mean = reference_time['mean'] if isinstance(reference_time, dict) else reference_time
            speedup = ref_mean / max_time if max_time > 0 else 0
            timing_info['reference_comparison'] = {
                'reference_time': ref_mean,
                'reference_time_stats': reference_time if isinstance(reference_time, dict) else None,
                'speedup': speedup,
                'faster': speedup >= 1
            }
    
    # Failed partitions
    failed_partitions = [
        {'file': r['file'], 'exit_code': r['exit_code']}
        for r in results
        if r['exit_code'] not in [0, 124]
    ]
    
    # Build summary structure
    summary = {
        'total_partitions': len(results),
        'status_counts': {
            'success': success_count,
            'timeout': timeout_count,
            'failed': failed_count
        },
        'output_comparison': {
            'matching': matching_count,
            'differing': differing_count,
            'differing_partitions': differing_partitions
        } if reference_output is not None else None,
        'combined_output_comparison': combined_comparison if combined_comparison is not None else None,
        'timing': timing_info,
        'failed_partitions': failed_partitions,
        'partition_details': [
            {
                'file': r['file'],
                'status': r['status'],
                'exit_code': r['exit_code'],
                'time_stats': r.get('time_stats', {}),
                'output_matches': r.get('output_matches'),
                'match_percentage': r.get('match_percentage'),
                'step_by_step_timing': r.get('step_by_step_timing')
            }
            for r in results
        ]
    }
    
    # Save to JSON file
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)


# =============================================================================
# TOP-LEVEL ORCHESTRATOR
# =============================================================================

def run_enfguard_on_partitions(
    mfotl_dir: str, 
    sig_file: str, 
    log_file: str, 
    func_file: str, 
    reference_mfotl: Optional[str] = None, 
    timeout: Optional[int] = None, 
    output_dir: Optional[str] = None, 
    label: bool = False,
    json_summary: Optional[str] = None,
    step_by_step: bool = False,
    repeat_runs: int = 1
) -> int:
    """
    Run enfguard on all MFOTL files in the given directory.
    
    Args:
        mfotl_dir: Directory containing partition MFOTL files
        sig_file: Path to signature file
        log_file: Path to log file
        func_file: Path to function file
        reference_mfotl: Optional reference MFOTL file to compare against
        timeout: Optional timeout in seconds for each run (or per step if step_by_step)
        output_dir: Optional directory to save partition outputs and diffs
        label: Optional flag to enable label output (shows which rules caused actions)
        json_summary: Optional path to save JSON summary of results
        step_by_step: Optional flag to enable step-by-step execution mode
        repeat_runs: Number of times to run each partition for timing measurements
    
    Returns:
        0 if all partitions succeeded, 1 otherwise
    """
    # Setup output directories
    output_subdir = None
    diff_subdir = None
    if output_dir:
        output_subdir, diff_subdir = setup_output_directories(output_dir)
    
    # Run reference file first if provided
    reference_output = None
    reference_time = None
    if reference_mfotl:
        reference_output, reference_time = run_reference_enfguard(
            reference_mfotl, sig_file, log_file, func_file, 
            label, timeout, output_subdir, step_by_step, repeat_runs
        )
    
    # Find all .mfotl files in the directory
    mfotl_files = sorted(Path(mfotl_dir).glob("*.mfotl"))
    
    if not mfotl_files:
        print(f"No .mfotl files found in {mfotl_dir}")
        return 0
    
    mode_str = "STEP-BY-STEP" if step_by_step else "STANDARD"
    print(f"RUNNING PARTITIONS ({len(mfotl_files)} files) - {mode_str} MODE")
    print(f"  Signature: {sig_file}")
    print(f"  Log: {log_file}")
    print(f"  Functions: {func_file}")
    if repeat_runs > 1:
        print(f"  Repeat runs: {repeat_runs} (timing only)")
    if timeout:
        timeout_scope = "per step" if step_by_step else "per partition"
        print(f"  Timeout: {timeout}s {timeout_scope}")
    
    # Run enfguard on all partition files
    results = []
    for mfotl_file in mfotl_files:
        result = run_partition_enfguard(
            mfotl_file, sig_file, log_file, func_file,
            label, timeout, reference_output,
            output_subdir, diff_subdir,
            step_by_step=step_by_step,
            repeat_runs=repeat_runs
        )
        results.append(result)
    
    # Combine all partition outputs and compare to reference
    combined_comparison = None
    if reference_output is not None:
        combined_comparison = combine_and_compare_partitions(
            results, reference_output, 
            output_subdir, diff_subdir
        )
    
    # Print summary
    print_summary(results, reference_output, reference_time)
    
    # Save JSON summary if requested
    if json_summary:
        save_json_summary(results, reference_output, reference_time, json_summary, combined_comparison)
        print(f"\nJSON summary saved to: {json_summary}")
    
    # Return exit code: 0 if all succeeded, 1 if any failed or timed out
    success_count = sum(1 for r in results if r['exit_code'] == 0)
    if success_count == len(results):
        return 0
    return 1


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Run enfguard on all partition MFOTL files in a directory',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('mfotl_dir', help='Directory containing partition MFOTL files')
    parser.add_argument('-sig', '--signature', required=True, help='Path to signature file')
    parser.add_argument('-log', '--log', required=True, help='Path to log file')
    parser.add_argument('-func', '--functions', required=True, help='Path to functions file')
    parser.add_argument('-ref', '--reference', default=None,
                       help='Reference MFOTL file to compare timing against (optional)')
    parser.add_argument('-t', '--timeout', type=int, default=None,
                       help='Timeout in seconds for each partition (optional)')
    parser.add_argument('-o', '--output-dir', default=None,
                       help='Directory to save partition outputs and diffs (optional)')
    parser.add_argument('-l', '--label', action='store_true',
                       help='Enable label output to show which rules caused actions (optional)')
    parser.add_argument('-j', '--json-summary', default=None,
                       help='Path to save JSON summary of results (optional)')
    parser.add_argument('-s', '--step-by-step', action='store_true',
                       help='Run enforcement in step-by-step mode, measuring time at each timestamp (optional)')
    parser.add_argument('-r', '--repeat', type=int, default=1,
                       help='Number of times to run each partition for timing measurements (default: 1)')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.isdir(args.mfotl_dir):
        print(f"Error: {args.mfotl_dir} is not a directory")
        sys.exit(1)
    
    if not os.path.isfile(args.signature):
        print(f"Error: Signature file not found: {args.signature}")
        sys.exit(1)
    
    if not os.path.isfile(args.log):
        print(f"Error: Log file not found: {args.log}")
        sys.exit(1)
    
    if not os.path.isfile(args.functions):
        print(f"Error: Functions file not found: {args.functions}")
        sys.exit(1)
    
    if args.reference and not os.path.isfile(args.reference):
        print(f"Error: Reference MFOTL file not found: {args.reference}")
        sys.exit(1)
    
    exit_code = run_enfguard_on_partitions(
        args.mfotl_dir,
        args.signature,
        args.log,
        args.functions,
        args.reference,
        args.timeout,
        args.output_dir,
        args.label,
        args.json_summary,
        args.step_by_step,
        args.repeat
    )
    sys.exit(exit_code)
