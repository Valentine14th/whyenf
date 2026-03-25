#!/usr/bin/env python3
"""
Regenerate all plots in a results folder.

This script will regenerate:
1. Per-log plots in each log subdirectory:
   - step_by_step_timing_plot.png
   - partition_differences_plot.png

2. Summary plots at the results folder level:
   - summary_matching_status.png
   - summary_speedup.png
   - summary_complexity_vs_time.png
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def find_log_subdirectories(results_dir: Path):
    """
    Find all log subdirectories that contain enforcement_results.json.
    
    Args:
        results_dir: Path to results directory
        
    Returns:
        List of (log_subdir_path, log_name) tuples
    """
    log_subdirs = []
    
    # Look for directories starting with 'log_'
    for item in results_dir.iterdir():
        if item.is_dir() and item.name.startswith('log_'):
            enforcement_file = item / 'enforcement_results.json'
            if enforcement_file.exists():
                log_subdirs.append((item, item.name))
    
    return log_subdirs


def create_multi_log_summary(results_dir: Path, log_subdirs: list):
    """
    Create multi_log_summary.json from individual enforcement results.
    
    Args:
        results_dir: Path to results directory
        log_subdirs: List of (log_subdir_path, log_name) tuples
        
    Returns:
        Path to created summary file, or None if creation failed
    """
    print(f"Creating multi_log_summary.json from {len(log_subdirs)} log results...")
    
    log_results_summary = []
    
    for log_dir, log_name in log_subdirs:
        enforcement_file = log_dir / 'enforcement_results.json'
        
        if not enforcement_file.exists():
            continue
        
        try:
            with open(enforcement_file, 'r') as f:
                enforcement_data = json.load(f)
            
            # Extract high-level summary (without partition_details to keep it smaller)
            enforcement_summary = {
                'total_partitions': enforcement_data.get('total_partitions'),
                'status_counts': enforcement_data.get('status_counts'),
                'output_comparison': enforcement_data.get('output_comparison'),
                'combined_output_comparison': enforcement_data.get('combined_output_comparison'),
                'timing': enforcement_data.get('timing'),
                'failed_partitions': enforcement_data.get('failed_partitions')
            }
            
            # Extract log file name from log_name (remove 'log_' prefix)
            log_file_name = log_name.replace('log_', '', 1) + '.log'
            
            log_results_summary.append({
                'log_file': log_file_name,
                'log_path': str(log_dir),
                'output_subdir': log_name,
                'status': 'success',
                'enforcement_summary': enforcement_summary
            })
            
            print(f"  ✓ Loaded: {log_file_name}")
            
        except Exception as e:
            print(f"  ✗ Failed to load {log_name}: {e}")
            log_results_summary.append({
                'log_file': log_name.replace('log_', '', 1) + '.log',
                'log_path': str(log_dir),
                'output_subdir': log_name,
                'status': 'failed',
                'enforcement_summary': None
            })
    
    # Create summary structure
    summary = {
        'workflow_name': results_dir.name,
        'timestamp': datetime.now().isoformat(),
        'total_logs': len(log_subdirs),
        'successful_logs': sum(1 for r in log_results_summary if r['status'] == 'success'),
        'failed_logs': sum(1 for r in log_results_summary if r['status'] == 'failed'),
        'log_results': log_results_summary
    }
    
    # Write summary file
    summary_file = results_dir / 'multi_log_summary.json'
    try:
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Created: {summary_file}")
        return summary_file
    except Exception as e:
        print(f"✗ Failed to create summary file: {e}")
        return None


def regenerate_step_by_step_timing_plot(log_dir: Path, script_dir: Path, partition_names: dict = None):
    """
    Regenerate step-by-step timing plot for a log.
    
    Args:
        log_dir: Path to log subdirectory
        script_dir: Path to utils directory containing plotting scripts
        partition_names: Optional dict mapping partition filenames to custom names
        
    Returns:
        True if successful, False otherwise
    """
    enforcement_file = log_dir / 'enforcement_results.json'
    plots_dir = log_dir / 'plots'
    output_file = plots_dir / 'step_by_step_timing_plot.png'
    
    if not enforcement_file.exists():
        print(f"  ✗ Enforcement results not found: {enforcement_file}")
        return False
    
    plots_dir.mkdir(exist_ok=True)
    
    plot_script = script_dir / 'plot_step_by_step_timing.py'
    
    if not plot_script.exists():
        print(f"  ✗ Plotting script not found: {plot_script}")
        return False
    
    cmd = [
        sys.executable,
        str(plot_script),
        str(enforcement_file),
        '-o', str(output_file)
    ]
    
    # Add partition names file if provided
    if partition_names:
        import tempfile
        import json
        # Write partition names to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(partition_names, f)
            temp_names_file = f.name
        cmd.extend(['--partition-names', temp_names_file])
    else:
        temp_names_file = None
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"  ✓ Generated: {output_file.name}")
            return True
        else:
            print(f"  ✗ Failed to generate {output_file.name}")
            if result.stderr:
                print(f"    Error: {result.stderr[:200]}")
            return False
    
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout generating {output_file.name}")
        return False
    except Exception as e:
        print(f"  ✗ Error generating {output_file.name}: {e}")
        return False
    finally:
        # Clean up temp file if created
        if temp_names_file and os.path.exists(temp_names_file):
            os.remove(temp_names_file)




def regenerate_partition_differences_plot(log_dir: Path, script_dir: Path):
    """
    Regenerate partition differences plot for a log.
    
    Args:
        log_dir: Path to log subdirectory
        script_dir: Path to utils directory containing plotting scripts
        
    Returns:
        True if successful, False otherwise
    """
    diff_dir = log_dir / 'partition_outputs' / 'diff'
    plots_dir = log_dir / 'plots'
    output_file = plots_dir / 'partition_differences_plot.png'
    
    if not diff_dir.exists():
        print(f"  ✗ Diff directory not found: {diff_dir}")
        return False
    
    # Check if there are any diff files
    diff_files = list(diff_dir.glob('diff_*.json'))
    if not diff_files:
        print(f"  ⚠ No diff files found in {diff_dir.name}, skipping")
        return True  # Not an error, just no data
    
    plots_dir.mkdir(exist_ok=True)
    
    plot_script = script_dir / 'plot_diff_stats.py'
    
    if not plot_script.exists():
        print(f"  ✗ Plotting script not found: {plot_script}")
        return False
    
    cmd = [
        sys.executable,
        str(plot_script),
        str(diff_dir)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"  ✓ Generated: {output_file.name}")
            return True
        else:
            print(f"  ✗ Failed to generate {output_file.name}")
            if result.stderr:
                print(f"    Error: {result.stderr[:200]}")
            return False
    
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout generating {output_file.name}")
        return False
    except Exception as e:
        print(f"  ✗ Error generating {output_file.name}: {e}")
        return False


def regenerate_summary_plots(results_dir: Path, script_dir: Path, partition_names: dict = None):
    """
    Regenerate multi-log summary plots.
    
    Args:
        results_dir: Path to results directory
        script_dir: Path to utils directory containing plotting scripts
        partition_names: Optional dict mapping partition filenames to custom names
        
    Returns:
        True if successful, False otherwise
    """
    summary_file = results_dir / 'multi_log_summary.json'
    mfotl_dir = results_dir / 'mfotl'
    
    if not summary_file.exists():
        print(f"✗ Multi-log summary file not found: {summary_file}")
        return False
    
    if not mfotl_dir.exists():
        print(f"✗ MFOTL directory not found: {mfotl_dir}")
        return False
    
    plot_script = script_dir / 'plot_multi_log_summary.py'
    
    if not plot_script.exists():
        print(f"✗ Plotting script not found: {plot_script}")
        return False
    
    # Output prefix for plots
    plot_prefix = str(results_dir / 'summary')
    
    cmd = [
        sys.executable,
        str(plot_script),
        str(summary_file),
        str(results_dir),
        str(mfotl_dir),
        '-o', plot_prefix
    ]
    
    # Add partition names file if provided
    if partition_names:
        import tempfile
        import json
        # Write partition names to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(partition_names, f)
            temp_names_file = f.name
        cmd.extend(['--partition-names', temp_names_file])
    else:
        temp_names_file = None
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✓ Generated summary plots:")
            print(f"  - summary_matching_status.png")
            print(f"  - summary_speedup.png")
            print(f"  - summary_complexity_vs_time.png")
            return True
        else:
            print(f"✗ Failed to generate summary plots")
            if result.stderr:
                print(f"  Error: {result.stderr[:500]}")
            return False
    
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout generating summary plots")
        return False
    except Exception as e:
        print(f"✗ Error generating summary plots: {e}")
        return False
    finally:
        # Clean up temp file if created
        if temp_names_file and os.path.exists(temp_names_file):
            os.remove(temp_names_file)


def main():
    parser = argparse.ArgumentParser(
        description='Regenerate all plots in a results folder',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('results_dir',
                       help='Path to results directory (e.g., tests/partition/results/test)')
    parser.add_argument('--per-log-only', action='store_true',
                       help='Only regenerate per-log plots, skip summary plots')
    parser.add_argument('--summary-only', action='store_true',
                       help='Only regenerate summary plots, skip per-log plots')
    parser.add_argument('--partition-names', type=str,
                       help='JSON file with partition name mappings (e.g., {"partition_1106.mfotl": "Access Rights", ...})')
    parser.add_argument('--force-recreate-summary', action='store_true',
                       help='Force recreation of multi_log_summary.json from individual log results')
    
    args = parser.parse_args()
    
    results_dir = Path(args.results_dir).resolve()
    
    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        return 1
    
    if not results_dir.is_dir():
        print(f"Error: Not a directory: {results_dir}")
        return 1
    
    # Load partition names if provided
    partition_names = None
    if args.partition_names:
        import json
        partition_names_file = Path(args.partition_names)
        if not partition_names_file.exists():
            print(f"Error: Partition names file not found: {partition_names_file}")
            return 1
        try:
            with open(partition_names_file, 'r') as f:
                partition_names = json.load(f)
            print(f"Loaded {len(partition_names)} partition name mappings")
        except Exception as e:
            print(f"Error loading partition names file: {e}")
            return 1
    
    # Determine script directory (should be in utils/ relative to this script)
    script_dir = Path(__file__).parent.resolve()
    
    print(f"Results directory: {results_dir}")
    print(f"Script directory: {script_dir}")
    print()
    
    success_count = 0
    failure_count = 0
    
    # Regenerate per-log plots
    if not args.summary_only:
        log_subdirs = find_log_subdirectories(results_dir)
        
        if not log_subdirs:
            print("No log subdirectories found")
        else:
            print(f"Found {len(log_subdirs)} log subdirectories\n")
            
            for log_dir, log_name in log_subdirs:
                print(f"Processing {log_name}...")
                
                # Step-by-step timing plot
                if regenerate_step_by_step_timing_plot(log_dir, script_dir, partition_names):
                    success_count += 1
                else:
                    failure_count += 1
                
                # Partition differences plot
                if regenerate_partition_differences_plot(log_dir, script_dir):
                    success_count += 1
                else:
                    failure_count += 1
                
                print()
    
    # Regenerate summary plots
    if not args.per_log_only:
        print("Generating multi-log summary plots...")
        
        # Check if summary file exists or needs to be recreated
        summary_file = results_dir / 'multi_log_summary.json'
        should_create_summary = not summary_file.exists() or args.force_recreate_summary
        
        if should_create_summary:
            if summary_file.exists() and args.force_recreate_summary:
                print(f"Recreating multi_log_summary.json (forced)...")
            else:
                print(f"multi_log_summary.json not found, creating from log results...")
            
            log_subdirs = find_log_subdirectories(results_dir)
            if not log_subdirs:
                print("✗ No log subdirectories found, cannot create summary")
                failure_count += 3
            else:
                created_summary = create_multi_log_summary(results_dir, log_subdirs)
                if not created_summary:
                    print("✗ Failed to create multi_log_summary.json")
                    failure_count += 3
                else:
                    # Proceed with plot generation
                    if regenerate_summary_plots(results_dir, script_dir, partition_names):
                        success_count += 3  # Three summary plots
                    else:
                        failure_count += 3
        else:
            # Summary file exists, proceed with plot generation
            if regenerate_summary_plots(results_dir, script_dir, partition_names):
                success_count += 3  # Three summary plots
            else:
                failure_count += 3
        print()
    
    # Print summary
    print("=" * 60)
    print(f"Regeneration complete:")
    print(f"  ✓ Successful: {success_count}")
    if failure_count > 0:
        print(f"  ✗ Failed: {failure_count}")
    print("=" * 60)
    
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    exit(main())
