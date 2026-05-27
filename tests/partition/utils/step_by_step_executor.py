#!/usr/bin/env python3
"""
Step-by-step enforcement executor.
Parses log files and runs enforcement incrementally, tracking each block with a timepoint.
Uses timepoints (incremental counters) to identify and track enforcement blocks.
"""

import os
import re
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


def extract_timestamps(log_lines: List[str]) -> Tuple[List[int], List[int]]:
    """
    Extract timestamps from log lines and check for missing tick() calls.
    
    Args:
        log_lines: List of log file lines
        
    Returns:
        Tuple of (timestamps, missing_ticks)
    """
    timestamps = []
    timestamp_has_tick = set()
    
    for line in log_lines:
        match = re.match(r'@(\d+)', line)
        if match:
            timestamp = int(match.group(1))
            timestamps.append(timestamp)
            if 'tick()' in line:
                timestamp_has_tick.add(timestamp)
    
    # All timestamps except 1 should have tick()
    unique_timestamps = set(timestamps)
    missing_ticks = sorted([ts for ts in unique_timestamps if ts > 1 and ts not in timestamp_has_tick])
    
    return timestamps, missing_ticks


def detect_block_type(output_line: str) -> Tuple[Optional[str], bool]:
    """
    Detect block type and action from output line.
    
    Args:
        output_line: Single line of enforcer output
        
    Returns:
        Tuple of (block_type, has_action)
    """
    if 'reactively commands:' in output_line:
        return 'reactive', True
    elif 'proactively commands:' in output_line:
        return 'proactive', True
    elif 'nothing to do proactively' in output_line:
        return 'proactive', False
    return None, False


def detect_block_completion(output_line: str, block_type: Optional[str]) -> bool:
    """
    Check if a block has completed based on its type.
    
    Block completion patterns:
    - Reactive with action: ends with "OK."
    - Reactive no action: ends with "[Enforcer] ... OK."
    - Proactive with action: ends with "OK."
    - Proactive no action: ends with "nothing to do proactively"
    
    Args:
        output_line: Single line of enforcer output
        block_type: Current block type ('reactive', 'proactive', or None)
        
    Returns:
        True if completion detected for this block type
    """
    line = output_line.strip()
    
    # Proactive block with no action
    if 'nothing to do proactively' in line:
        return True
    
    # Reactive block with no action (like "[Enforcer] @1 OK.")
    if block_type is None and re.search(r'\[Enforcer\].*OK\.\s*$', line):
        return True
    
    # Reactive or proactive block with action (ends with just "OK.")
    if block_type in ['reactive', 'proactive'] and re.search(r'^.*OK\.\s*$', line) and '[Enforcer]' not in line:
        return True
    
    return False


def calculate_block_statistics(step_results: List[Dict]) -> Dict:
    """
    Calculate statistics about block types and actions.
    
    Args:
        step_results: List of step result dictionaries
        
    Returns:
        Dictionary with block counts
    """
    stats = defaultdict(int)
    
    for step in step_results:
        block_type = step.get('block_type')
        has_action = step.get('has_action', False)
        
        if block_type == 'reactive':
            stats['reactive_total'] += 1
            if has_action:
                stats['reactive_with_action'] += 1
            else:
                stats['reactive_no_action'] += 1
        elif block_type == 'proactive':
            stats['proactive_total'] += 1
            if has_action:
                stats['proactive_with_action'] += 1
            else:
                stats['proactive_no_action'] += 1
    
    return dict(stats)


def run_enfguard_step_by_step(
    mfotl_file: str,
    sig_file: str,
    log_file: str,
    func_file: str,
    label: bool = False,
    timeout: Optional[int] = None,
    output_dir: Optional[str] = None,
    binary: str = './enfguard'
) -> Dict:
    """
    Run enfguard step-by-step in interactive mode, measuring time at each timepoint.
    Each log line produces one enforcement block which is assigned a sequential timepoint.
    
    Args:
        mfotl_file: Path to MFOTL formula file
        sig_file: Path to signature file
        log_file: Path to log file
        func_file: Path to functions file
        label: Enable label output
        timeout: Optional timeout in seconds (total, not per step)
        output_dir: Optional directory (currently unused - for future extension)
        binary: Path to enfguard binary (default: './enfguard')
        
    Returns:
        Dictionary with step-by-step results
    """
    # Read log file lines
    with open(log_file, 'r') as f:
        log_lines = [line.strip() for line in f if line.strip()]
    
    if not log_lines:
        return {
            'status': 'error',
            'message': 'No events found in log file',
            'steps': []
        }
    
    # Extract timestamps and check for missing tick() calls
    timestamps, missing_ticks = extract_timestamps(log_lines)
    
    if missing_ticks:
        print(f"\n⚠ WARNING: Log file is missing tick() calls at timestamps: {missing_ticks}")
        print(f"  Each timestamp (except @1) should have a tick() line.")
        print(f"  Expected format: '@N tick();' before other events at timestamp N")
        print(f"  This may cause the workflow to produce incorrect results.\n")
    
    # Build enfguard command (without -log flag for interactive mode)
    cmd = [
        binary,
        "-sig", sig_file,
        "-formula", mfotl_file,
        "-func", func_file
    ]
    
    if label:
        cmd.append("-label")
    
    # Start enfguard process
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            cwd=os.getcwd()
        )
    except Exception as e:
        error_msg = f'Failed to start enfguard: {e}'
        print(f"✗ ERROR: {error_msg}")
        return {
            'status': 'error',
            'message': error_msg,
            'steps': []
        }
    
    step_results = []
    cumulative_time = 0.0
    all_stdout = []
    timepoint = 0
    
    try:
        # Wait for enfguard to be ready before starting timing
        time.sleep(3) 
        
        # Feed log lines one by one and measure timing
        for i, (line, timestamp) in enumerate(zip(log_lines, timestamps)):           
            step_start = time.time()
            process.stdin.write(line + "\n")
            process.stdin.flush()
            
            # Read output until we get completion signal for this block
            completed = False
            block_output = []
            step_stderr = []
            block_type = None
            has_action = False
            
            while True:
                output_line = process.stdout.readline()
                if not output_line:
                    stderr_output = process.stderr.read()
                    if stderr_output:
                        step_stderr.append(stderr_output)
                    break
                
                block_output.append(output_line)
                all_stdout.append(output_line)
                
                # Detect block type from output
                detected_type, detected_action = detect_block_type(output_line)
                if detected_type:
                    block_type = detected_type
                    has_action = detected_action
                
                # Check if block completed
                if detect_block_completion(output_line, block_type):
                    completed = True
                    if block_type is None:
                        block_type = 'reactive'
                        has_action = False
                    break
            
            step_time = time.time() - step_start
            cumulative_time += step_time
            
            # Create step result
            block_desc = f"{block_type}-{'action' if has_action else 'noaction'}" if block_type else "unknown"
            step_result = {
                'timepoint': timepoint,
                'step_number': timepoint,
                'timestamp': timestamp,
                'line_number': i + 1,
                'exit_code': 0 if completed else 1,
                'step_time': step_time,
                'cumulative_time': cumulative_time,
                'completed': completed,
                'status': 'success' if completed else 'incomplete',
                'block_type': block_type,
                'has_action': has_action,
                'block_output': ''.join(block_output)
            }
            step_results.append(step_result)
            
            # Print step summary with microsecond precision
            status_emoji = "✓" if completed else "✗"
            print(f"{status_emoji} tp{timepoint} (@{timestamp}): {step_time:.6f}s - {block_desc}")
            
            # Print errors if encountered
            if not completed or step_stderr:
                if step_stderr:
                    print(f"    ERROR at tp{timepoint} (@{timestamp}):")
                    for err_line in ''.join(step_stderr).strip().split('\n'):
                        print(f"      {err_line}")
                
                # Check for errors in stdout
                block_text = step_result['block_output']
                if 'error' in block_text.lower() or 'exception' in block_text.lower():
                    print(f"    Output indicates error at tp{timepoint} (@{timestamp}):")
                    for out_line in block_text.strip().split('\n'):
                        if 'error' in out_line.lower() or 'exception' in out_line.lower():
                            print(f"      {out_line}")
            
            # Stop if we didn't get completion
            if not completed:
                print(f"Warning: No completion signal received for tp{timepoint} (timestamp {timestamp})")
                break
            
            timepoint += 1
    
    except Exception as e:
        error_msg = f"Exception during step-by-step execution: {e}"
        print(f"✗ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up process
        try:
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()
            process.terminate()
            process.wait(timeout=5)
        except Exception as e:
            print(f"Warning: Error closing enfguard process: {e}")
    
    # Calculate statistics
    successful_steps = [s for s in step_results if s['exit_code'] == 0]
    stdout_combined = ''.join(all_stdout)
    block_stats = calculate_block_statistics(step_results)
    
    # Parse output into blocks and save as JSON
    blocks_json = None
    if output_dir:
        try:
            from enforcer_diff import EnforcerBlock, blocks_to_json_file
            
            # Build blocks directly from step_results
            blocks = [
                EnforcerBlock(
                    timestamp=step['timestamp'],
                    raw_content=step['block_output'],
                    lines=step['block_output'].split('\n') if step['block_output'] else [],
                    block_type=step['block_type'],
                    has_action=step['has_action'],
                    timepoint=step['timepoint']
                )
                for step in step_results
            ]
            
            # Create timing map from step results
            timing_map = {
                step['timepoint']: {
                    'step_time': step.get('step_time'),
                    'cumulative_time': step.get('cumulative_time'),
                    'line_number': step.get('line_number'),
                    'block_type': step.get('block_type'),
                    'has_action': step.get('has_action'),
                    'status': step.get('status')
                }
                for step in step_results if 'timepoint' in step
            }
            
            # Save blocks as JSON with timing info
            parsed_output_dir = os.path.join(output_dir, "parsed_output")
            os.makedirs(parsed_output_dir, exist_ok=True)
            blocks_json_file = os.path.join(parsed_output_dir, "step_by_step_blocks.json")
            blocks_to_json_file(blocks, blocks_json_file, timing_map=timing_map)
            blocks_json = blocks_json_file
        except ImportError:
            pass
    
    return {
        'status': 'success' if len(successful_steps) == len(step_results) else 'partial',
        'total_lines': len(log_lines),
        'total_timepoints': timepoint,
        'total_steps': timepoint,
        'completed_steps': len(successful_steps),
        'total_time': cumulative_time,
        'steps': step_results,
        'timestamps': timestamps,
        'avg_step_time': cumulative_time / len(successful_steps) if successful_steps else 0.0,
        'stdout': stdout_combined,
        'blocks_json': blocks_json,
        **block_stats
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: step_by_step_executor.py <mfotl> <sig> <log> <func>")
        sys.exit(1)
    
    results = run_enfguard_step_by_step(
        sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], label=True
    )
    
    print("\n=== SUMMARY ===")
    print(f"Status: {results['status']}")
    print(f"Timepoints: {results['total_timepoints']}")
    print(f"Lines processed: {results['completed_steps']}/{results['total_lines']}")
    print(f"Total time: {results['total_time']:.6f}s")
    print(f"Avg per timepoint: {results['avg_step_time']:.6f}s")
    
    # Print block statistics
    reactive_total = results.get('reactive_total', 0)
    reactive_action = results.get('reactive_with_action', 0)
    reactive_no_action = results.get('reactive_no_action', 0)
    proactive_total = results.get('proactive_total', 0)
    proactive_action = results.get('proactive_with_action', 0)
    proactive_no_action = results.get('proactive_no_action', 0)
    
    print(f"Reactive blocks: {reactive_total} total ({reactive_action} with action, {reactive_no_action} no action)")
    print(f"Proactive blocks: {proactive_total} total ({proactive_action} with action, {proactive_no_action} no action)")
