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
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import specialized enforcer diff module
try:
    from enforcer_diff import (
        compare_enforcer_outputs, 
        save_comparison_report,
        save_comparison_json,
        parse_enforcer_output,
        combine_blocks_by_timestamp
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
    
    print(f"Output directory: {output_dir}")
    print(f"  - Outputs: {output_subdir}")
    print(f"  - Diffs: {diff_subdir}")
    print()
    
    return output_subdir, diff_subdir


def run_reference_enfguard(
    reference_mfotl: str,
    sig_file: str,
    log_file: str,
    func_file: str,
    label: bool,
    timeout: Optional[int],
    output_subdir: Optional[str]
) -> Tuple[Optional[str], Optional[float]]:
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
        
    Returns:
        Tuple of (reference_output, reference_time) or (None, None) if failed
    """
    print(f"RUNNING REFERENCE FILE: {reference_mfotl}")
    
    try:
        exit_code, stdout, stderr, elapsed_time = run_enfguard_command(
            reference_mfotl, sig_file, log_file, func_file, label, timeout
        )
        
        if exit_code == 0:
            print(f"✓ SUCCESS - Time: {elapsed_time:.2f}s")
            
            # Save reference output if output_subdir specified
            if output_subdir:
                ref_output_file = os.path.join(output_subdir, "reference_output.txt")
                with open(ref_output_file, 'w') as f:
                    f.write(stdout)
                print(f"  Saved output to: {ref_output_file}")
            
            print()
            return stdout, elapsed_time
            
        elif exit_code == 124:
            print(f"⏱ TIMEOUT - Time: {elapsed_time:.2f}s")
        else:
            print(f"✗ FAILED (exit code {exit_code}) - Time: {elapsed_time:.2f}s")
            print("Error output:")
            for line in stderr.split('\n')[:10]:
                print(f"  {line}")
                
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
    
    print()
    return None, None


def compare_and_save_output(
    partition_name: str,
    partition_output: str,
    reference_output: str,
    output_subdir: Optional[str],
    diff_subdir: Optional[str]
) -> Tuple[bool, Optional[float]]:
    """
    Compare partition output with reference and save results.
    
    Args:
        partition_name: Name of partition file
        partition_output: Partition output string
        reference_output: Reference output string
        output_subdir: Directory to save outputs
        diff_subdir: Directory to save diffs
        
    Returns:
        Tuple of (output_matches, match_percentage)
    """
    # Save partition output
    if output_subdir:
        partition_output_file = os.path.join(
            output_subdir, 
            f"{os.path.splitext(partition_name)[0]}_output.txt"
        )
        with open(partition_output_file, 'w') as f:
            f.write(partition_output)
    
    # Compare outputs
    if ENFORCER_DIFF_AVAILABLE:
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
        
        # Save specialized diff report if outputs differ
        if not output_matches and diff_subdir:
            diff_file = os.path.join(
                diff_subdir,
                f"{os.path.splitext(partition_name)[0]}_diff.json"
            )
            save_comparison_json(comparison, diff_file)
            return output_matches, match_percentage
        
        return output_matches, match_percentage
    else:
        # Fall back to basic string comparison
        output_matches = (partition_output == reference_output)
        
        # Save basic unified diff if outputs differ
        if not output_matches and diff_subdir:
            diff_file = os.path.join(
                diff_subdir,
                f"{os.path.splitext(partition_name)[0]}_diff.txt"
            )
            ref_lines = reference_output.splitlines(keepends=True)
            part_lines = partition_output.splitlines(keepends=True)
            diff = difflib.unified_diff(
                ref_lines,
                part_lines,
                fromfile='reference',
                tofile=partition_name,
                lineterm='\n'
            )
            with open(diff_file, 'w') as f:
                f.writelines(diff)
        
        return output_matches, None


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
    step_by_step: bool = False
) -> Dict:
    """
    Run enfguard on a single partition file and compare with reference.
    Optionally also collect step-by-step timing information.
    
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
        
    Returns:
        Dictionary with result information
    """
    partition_name = mfotl_file.name
    print(f"\n[{partition_name}] Running enfguard...")
    
    try:
        exit_code, stdout, stderr, elapsed_time = run_enfguard_command(
            str(mfotl_file), sig_file, log_file, func_file, label, timeout
        )
        
        if exit_code == 0:
            status = "✓ SUCCESS"
            
            # Compare with reference if available
            output_matches = None
            match_percentage = None
            
            if reference_output is not None:
                output_matches, match_percentage = compare_and_save_output(
                    partition_name, stdout, reference_output, 
                    output_subdir, diff_subdir
                )
                
                if output_matches:
                    print(f"[{partition_name}] {status} - Time: {elapsed_time:.2f}s - Output: ✓ MATCHES reference (100.00%)")
                else:
                    match_pct_str = f"{match_percentage:.2f}%" if match_percentage is not None else "unknown"
                    print(f"[{partition_name}] {status} - Time: {elapsed_time:.2f}s - Output: ✗ DIFFERS from reference ({match_pct_str} matching)")
                    if diff_subdir:
                        diff_file = os.path.join(diff_subdir, f"{os.path.splitext(partition_name)[0]}_diff.json")
                        print(f"  Detailed diff saved to: {diff_file}")
            else:
                print(f"[{partition_name}] {status} - Time: {elapsed_time:.2f}s")
            
            # Collect step-by-step timing if requested
            step_by_step_data = None
            if step_by_step and STEP_BY_STEP_AVAILABLE:
                print(f"[{partition_name}] Collecting step-by-step timing information...")
                try:
                    step_by_step_data = run_enfguard_step_by_step(
                        str(mfotl_file),
                        sig_file,
                        log_file,
                        func_file,
                        label=label,
                        timeout=timeout,
                        output_dir=None
                    )
                    avg_time = step_by_step_data.get('avg_step_time', 0.0)
                    print(f"[{partition_name}] Step-by-step: {step_by_step_data['total_steps']} steps, avg {avg_time:.3f}s/step")
                except Exception as e:
                    print(f"[{partition_name}] Warning: Step-by-step timing failed: {e}")
            
            return {
                'file': partition_name,
                'status': status,
                'exit_code': exit_code,
                'time': elapsed_time,
                'output_matches': output_matches,
                'match_percentage': match_percentage,
                'output': stdout,
                'step_by_step_timing': step_by_step_data
            }
            
        elif exit_code == 124:
            status = "⏱ TIMEOUT"
            print(f"[{partition_name}] {status} - Time: {elapsed_time:.2f}s")
        else:
            status = f"✗ FAILED (exit code {exit_code})"
            print(f"[{partition_name}] {status} - Time: {elapsed_time:.2f}s")
            print("Error output:")
            for line in stderr.split('\n')[:10]:
                print(f"  {line}")
        
        return {
            'file': partition_name,
            'status': status,
            'exit_code': exit_code,
            'time': elapsed_time,
            'output_matches': None,
            'match_percentage': None,
            'output': None,
            'step_by_step_timing': None
        }
        
    except Exception as e:
        print(f"[{partition_name}] ✗ EXCEPTION: {e}")
        return {
            'file': partition_name,
            'status': 'EXCEPTION',
            'exit_code': -1,
            'time': 0,
            'output_matches': None,
            'match_percentage': None,
            'output': None,
            'step_by_step_timing': None
        }


def combine_and_compare_partitions(
    results: List[Dict],
    reference_output: str,
    output_subdir: Optional[str],
    diff_subdir: Optional[str]
) -> None:
    """
    Combine all partition outputs and compare to reference.
    
    Args:
        results: List of partition result dictionaries
        reference_output: Reference output string
        output_subdir: Directory to save combined output
        diff_subdir: Directory to save combined diff
    """
    if not ENFORCER_DIFF_AVAILABLE:
        return
    
    # Collect all successful partition outputs
    successful_outputs = [r['output'] for r in results if r['output'] is not None]
    
    if not successful_outputs:
        return
    
    print("\n" + "="*80)
    print("COMBINED PARTITION OUTPUT COMPARISON")
    print("="*80)
    
    # Parse all partition outputs into blocks
    all_blocks = []
    for output in successful_outputs:
        blocks = parse_enforcer_output(output)
        all_blocks.extend(blocks)
    
    # Combine blocks by timestamp
    combined_blocks = combine_blocks_by_timestamp(all_blocks)
    
    # Reconstruct combined output as text
    combined_output_lines = [block.raw_content for block in combined_blocks]
    combined_output = '\n'.join(combined_output_lines)
    
    # Save combined output
    if output_subdir:
        combined_output_file = os.path.join(output_subdir, "combined_partitions_output.txt")
        with open(combined_output_file, 'w') as f:
            f.write(combined_output)
        print(f"Combined output saved to: {combined_output_file}")
    
    # Compare combined output to reference
    combined_comparison = compare_enforcer_outputs(
        reference_output,
        combined_output,
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
        
        # Save combined diff report as JSON
        if diff_subdir:
            combined_diff_file = os.path.join(diff_subdir, "combined_partitions_diff.json")
            save_comparison_json(combined_comparison, combined_diff_file)
            print(f"  Detailed diff saved to: {combined_diff_file}")


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
        total_time = sum(r['time'] for r in successful_results)
        avg_time = total_time / len(successful_results)
        min_time = min(r['time'] for r in successful_results)
        max_time = max(r['time'] for r in successful_results)
        fastest_partition = min(successful_results, key=lambda r: r['time'])
        slowest_partition = max(successful_results, key=lambda r: r['time'])
        
        print(f"\nTiming (successful runs only):")
        print(f"  Total time (sequential): {total_time:.2f}s")
        print(f"  Average time: {avg_time:.2f}s")
        print(f"  Min time (fastest): {min_time:.2f}s - {fastest_partition['file']}")
        print(f"  Max time (slowest): {max_time:.2f}s - {slowest_partition['file']}")
        
        if reference_time is not None:
            speedup = reference_time / max_time if max_time > 0 else 0
            print(f"\nComparison to reference (parallel execution):")
            print(f"  Reference time: {reference_time:.2f}s")
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
    json_file: str
) -> None:
    """
    Save comprehensive results summary as JSON.
    
    Args:
        results: List of partition result dictionaries
        reference_output: Optional reference output for comparison
        reference_time: Optional reference execution time
        json_file: Path to save JSON summary
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
        total_time = sum(r['time'] for r in successful_results)
        avg_time = total_time / len(successful_results)
        min_time = min(r['time'] for r in successful_results)
        max_time = max(r['time'] for r in successful_results)
        fastest_partition = min(successful_results, key=lambda r: r['time'])
        slowest_partition = max(successful_results, key=lambda r: r['time'])
        
        timing_info = {
            'total_sequential_time': total_time,
            'average_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'fastest_partition': {
                'file': fastest_partition['file'],
                'time': fastest_partition['time']
            },
            'slowest_partition': {
                'file': slowest_partition['file'],
                'time': slowest_partition['time']
            }
        }
        
        if reference_time is not None:
            speedup = reference_time / max_time if max_time > 0 else 0
            timing_info['reference_comparison'] = {
                'reference_time': reference_time,
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
        'timing': timing_info,
        'failed_partitions': failed_partitions,
        'partition_details': [
            {
                'file': r['file'],
                'status': r['status'],
                'exit_code': r['exit_code'],
                'time': r['time'],
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
    step_by_step: bool = False
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
            label, timeout, output_subdir
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
            step_by_step=step_by_step
        )
        results.append(result)
    
    # Combine all partition outputs and compare to reference
    if reference_output is not None:
        combine_and_compare_partitions(
            results, reference_output, 
            output_subdir, diff_subdir
        )
    
    # Print summary
    print_summary(results, reference_output, reference_time)
    
    # Save JSON summary if requested
    if json_summary:
        save_json_summary(results, reference_output, reference_time, json_summary)
        print(f"\nJSON summary saved to: {json_summary}")
    
    # Return exit code: 0 if all succeeded, 1 if any failed or timed out
    success_count = sum(1 for r in results if r['exit_code'] == 0)
    if success_count == len(results):
        return 0
    return 1


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
        args.step_by_step
    )
    sys.exit(exit_code)
