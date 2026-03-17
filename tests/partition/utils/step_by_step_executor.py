#!/usr/bin/env python3
"""
Step-by-step enforcement executor.
Parses log files by timestamp and runs enforcement incrementally.
"""

import os
import re
import subprocess
import time
from typing import Dict, List, Optional


def detect_completion(output: str, timestamp: int) -> bool:
    """
    Check if enforcement completed for the given timestamp.
    
    Args:
        output: Enforcer output text
        timestamp: The timestamp to check for completion
        
    Returns:
        True if completion detected for this timestamp
    """
    # Look for "[Enforcer] @{timestamp} OK." or just "OK." at end of output
    patterns = [
        rf'\[Enforcer\]\s+@{timestamp}\s+OK\.',
        r'OK\.\s*$'
    ]
    
    for pattern in patterns:
        if re.search(pattern, output, re.MULTILINE):
            return True
    
    return False


def run_enfguard_step_by_step(
    mfotl_file: str,
    sig_file: str,
    log_file: str,
    func_file: str,
    label: bool = False,
    timeout: Optional[int] = None,
    output_dir: Optional[str] = None
) -> Dict:
    """
    Run enfguard step-by-step in interactive mode, measuring time at each timestamp.
    
    Args:
        mfotl_file: Path to MFOTL formula file
        sig_file: Path to signature file
        log_file: Path to log file
        func_file: Path to functions file
        label: Enable label output
        timeout: Optional timeout in seconds (total, not per step)
        output_dir: Optional directory (currently unused - for future extension)
        
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
    
    # Extract timestamps for tracking
    timestamps = []
    for line in log_lines:
        match = re.match(r'@(\d+)', line)
        if match:
            timestamps.append(int(match.group(1)))
    
    # Build enfguard command (without -log flag for interactive mode)
    cmd = [
        "./enfguard",
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
        return {
            'status': 'error',
            'message': f'Failed to start enfguard: {e}',
            'steps': []
        }
    
    step_results = []
    cumulative_time = 0.0
    
    try:
        # Feed log lines one by one and measure timing
        for i, (line, timestamp) in enumerate(zip(log_lines, timestamps)):           
            step_start = time.time()
            process.stdin.write(line + "\n")
            process.stdin.flush()
            
            # Read output until we get completion signal for this timestamp
            completed = False
            
            while True:
                output_line = process.stdout.readline()
                if not output_line:
                    # Process ended unexpectedly
                    break
                
                # Check if this line indicates completion for current timestamp
                if detect_completion(output_line, timestamp):
                    completed = True
                    break
            
            step_time = time.time() - step_start
            cumulative_time += step_time
            
            step_result = {
                'timestamp': timestamp,
                'step_number': i + 1,
                'exit_code': 0 if completed else 1,
                'step_time': step_time,
                'cumulative_time': cumulative_time,
                'completed': completed,
                'status': 'success' if completed else 'incomplete'
            }
            
            step_results.append(step_result)
            
            # Print step summary
            status_emoji = "✓" if completed else "✗"
            completion_str = "completed" if completed else "no completion signal"
            print(f"{status_emoji} @{timestamp}: {step_time:.3f}s (cumulative: {cumulative_time:.3f}s) - {completion_str}")
            
            # Stop if we didn't get completion
            if not completed:
                print(f"Warning: No completion signal received for timestamp {timestamp}")
                break
    
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
    
    return {
        'status': 'success' if len(successful_steps) == len(step_results) else 'partial',
        'total_steps': len(timestamps),
        'completed_steps': len(successful_steps),
        'total_time': cumulative_time,
        'steps': step_results,
        'timestamps': timestamps,
        'avg_step_time': cumulative_time / len(successful_steps) if successful_steps else 0.0
    }


if __name__ == "__main__":
    # Simple test
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: step_by_step_executor.py <mfotl> <sig> <log> <func>")
        sys.exit(1)
    
    results = run_enfguard_step_by_step(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
        label=True
    )
    
    print("\n=== SUMMARY ===")
    print(f"Status: {results['status']}")
    print(f"Steps: {results['completed_steps']}/{results['total_steps']}")
    print(f"Total time: {results['total_time']:.3f}s")
    print(f"Avg step time: {results['avg_step_time']:.3f}s")
