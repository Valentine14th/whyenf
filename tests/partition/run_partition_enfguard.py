#!/usr/bin/env python3
"""
Run enfguard on all partition MFOTL files in a directory.
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path


def run_enfguard_on_partitions(mfotl_dir, sig_file, log_file, func_file, reference_mfotl=None, timeout=None):
    """
    Run enfguard on all MFOTL files in the given directory.
    
    Args:
        mfotl_dir: Directory containing partition MFOTL files
        sig_file: Path to signature file
        log_file: Path to log file
        func_file: Path to function file
        reference_mfotl: Optional reference MFOTL file to compare against
        timeout: Optional timeout in seconds for each run
    
    Returns:
        0 if all partitions succeeded, 1 otherwise
    """
    reference_time = None
    
    # Run reference file first if provided
    if reference_mfotl:
        print(f"RUNNING REFERENCE FILE: {reference_mfotl}")
        
        cmd = ["./enfguard", 
               "-sig", sig_file,
               "-formula", reference_mfotl,
               "-log", log_file,
               "-func", func_file]
        
        if timeout:
            cmd = ["timeout", str(timeout)] + cmd
        
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            reference_time = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✓ SUCCESS - Time: {reference_time:.2f}s")
            elif result.returncode == 124:
                print(f"⏱ TIMEOUT - Time: {reference_time:.2f}s")
                reference_time = None  # Don't compare if timed out
            else:
                print(f"✗ FAILED (exit code {result.returncode}) - Time: {reference_time:.2f}s")
                print("Error output:")
                for line in result.stderr.split('\n')[:10]:
                    print(f"  {line}")
                reference_time = None  # Don't compare if failed
                
        except Exception as e:
            print(f"✗ EXCEPTION: {e}")
            reference_time = None
        
        print()
    
    # Find all .mfotl files in the directory
    mfotl_files = sorted(Path(mfotl_dir).glob("*.mfotl"))
    
    if not mfotl_files:
        print(f"No .mfotl files found in {mfotl_dir}")
        return
    
    print(f"RUNNING PARTITIONS ({len(mfotl_files)} files)")
    print(f"  Signature: {sig_file}")
    print(f"  Log: {log_file}")
    print(f"  Functions: {func_file}")
    if timeout:
        print(f"  Timeout: {timeout}s per partition")
    
    results = []
    for mfotl_file in mfotl_files:
        partition_name = mfotl_file.name
        print(f"\n[{partition_name}] Running enfguard...")
        
        # Build command
        cmd = ["./enfguard", 
               "-sig", sig_file,
               "-formula", str(mfotl_file),
               "-log", log_file,
               "-func", func_file]
        
        # Add timeout if specified
        if timeout:
            cmd = ["timeout", str(timeout)] + cmd
        
        try:
            # Run enfguard and time it
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            elapsed_time = time.time() - start_time
            
            # Check exit code
            if result.returncode == 0:
                status = "✓ SUCCESS"
            elif result.returncode == 124:  # timeout exit code
                status = "⏱ TIMEOUT"
            else:
                status = f"✗ FAILED (exit code {result.returncode})"
            
            print(f"[{partition_name}] {status} - Time: {elapsed_time:.2f}s")
            
            # Show first few lines of output if there's an error
            if result.returncode not in [0, 124]:
                print("Error output:")
                for line in result.stderr.split('\n')[:10]:
                    print(f"  {line}")
            
            results.append({
                'file': partition_name,
                'status': status,
                'exit_code': result.returncode,
                'time': elapsed_time
            })
            
        except Exception as e:
            print(f"[{partition_name}] ✗ EXCEPTION: {e}")
            results.append({
                'file': partition_name,
                'status': 'EXCEPTION',
                'exit_code': -1,
                'time': 0
            })
    
    # Print summary
    print("SUMMARY")
    
    success_count = sum(1 for r in results if r['exit_code'] == 0)
    timeout_count = sum(1 for r in results if r['exit_code'] == 124)
    failed_count = sum(1 for r in results if r['exit_code'] not in [0, 124])
    
    print(f"Total: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Timeout: {timeout_count}")
    print(f"Failed: {failed_count}")
    
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
    
    if failed_count > 0:
        print("\nFailed partitions:")
        for r in results:
            if r['exit_code'] not in [0, 124]:
                print(f"  - {r['file']} (exit code {r['exit_code']})")
    
    # Return exit code: 0 if all succeeded, 1 if any failed or timed out
    if failed_count > 0 or timeout_count > 0:
        return 1
    return 0


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
        args.timeout
    )
    sys.exit(exit_code)
