#!/usr/bin/env python3
"""
Plot step-by-step timing results from partition enforcement.
Shows runtime per step for each partition with reference lines for batch and total time.
"""

import argparse
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def plot_step_by_step_timing(json_file: str, output_file: str = None):
    """
    Plot step-by-step timing from enforcement results JSON.
    
    Args:
        json_file: Path to partition_enforcement_results.json
        output_file: Optional path to save the plot (default: show interactive plot)
    """
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract partition details
    partitions = data.get('partition_details', [])
    
    if not partitions:
        print("No partition data found in JSON file")
        return
    
    # Filter partitions that have step-by-step timing
    partitions_with_timing = [
        p for p in partitions 
        if p.get('step_by_step_timing') and p['step_by_step_timing'].get('steps')
    ]
    
    if not partitions_with_timing:
        print("No step-by-step timing data found")
        return
    
    print(f"Plotting timing for {len(partitions_with_timing)} partitions")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Colors for different partitions
    colors = plt.cm.tab10(np.linspace(0, 1, len(partitions_with_timing)))
    
    # Track batch and interactive times for reference lines
    batch_times = []
    total_times = []
    
    # Plot each partition
    for idx, partition in enumerate(partitions_with_timing):
        partition_name = partition['file'].replace('minitwit_gdpr_4_partition_', 'P').replace('.mfotl', '')
        steps = partition['step_by_step_timing']['steps']
        batch_time = partition['time_stats']['mean']
        total_time = partition['step_by_step_timing']['total_time_stats']['mean']
        
        batch_times.append(batch_time)
        total_times.append(total_time)
        
        # Extract step numbers and step times (use mean from stats)
        step_numbers = [s['step_number'] for s in steps]
        step_times = [s['step_time_stats']['mean'] for s in steps]
        step_stds = [s['step_time_stats']['std'] for s in steps]
        
        # Check if multiple runs were performed (std > 0 indicates repeated runs)
        num_runs = partition['step_by_step_timing'].get('num_runs', 1)
        has_variance = num_runs > 1 and any(std > 0 for std in step_stds)
        
        if has_variance:
            # Plot line with shaded error region (std)
            ax.plot(step_numbers, step_times, 
                    marker='o', markersize=4, 
                    linewidth=1.5, 
                    label=partition_name, 
                    color=colors[idx],
                    alpha=0.8)
            
            # Add shaded region for standard deviation
            step_times_array = np.array(step_times)
            step_stds_array = np.array(step_stds)
            ax.fill_between(step_numbers, 
                           step_times_array - step_stds_array, 
                           step_times_array + step_stds_array,
                           color=colors[idx], alpha=0.2)
        else:
            # Plot line without error region (single run)
            ax.plot(step_numbers, step_times, 
                    marker='o', markersize=4, 
                    linewidth=1.5, 
                    label=partition_name, 
                    color=colors[idx],
                    alpha=0.8)
    
    # Calculate average times for summary stats (but don't plot them)
    avg_batch_time = np.mean(batch_times)
    avg_total_time = np.mean(total_times)
    
    # Check if any partition has multiple runs
    any_multiple_runs = any(p['step_by_step_timing'].get('num_runs', 1) > 1 for p in partitions_with_timing)
    
    # Formatting
    ax.set_xlabel('Step Number', fontsize=12, fontweight='bold')
    ax.set_ylabel('Time (seconds)', fontsize=12, fontweight='bold')
    title = 'Step-by-Step Enforcement Timing per Partition'
    if any_multiple_runs:
        title += ' (shaded regions show ±1 std dev)'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    
    # Set y-axis to log scale if there's a large range
    step_times_all = [s['step_time_stats']['mean'] for p in partitions_with_timing for s in p['step_by_step_timing']['steps']]
    if max(step_times_all) / min(step_times_all) > 100:
        ax.set_yscale('log')
        ax.set_ylabel('Time (seconds, log scale)', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    else:
        plt.show()
    
    # Print summary statistics
    print("\n=== Timing Summary ===")
    print(f"Average Batch Time: {avg_batch_time:.3f}s")
    print(f"Average Total Time (step-by-step): {avg_total_time:.3f}s")
    print(f"Overhead: {avg_total_time - avg_batch_time:.3f}s ({((avg_total_time/avg_batch_time - 1) * 100):.1f}%)")
    
    # Per-partition summary
    print("\nPer-Partition Details:")
    for idx, partition in enumerate(partitions_with_timing):
        partition_name = partition['file'].replace('minitwit_gdpr_4_partition_', 'P').replace('.mfotl', '')
        batch_time = partition['time_stats']['mean']
        total_time_stats = partition['step_by_step_timing']['total_time_stats']
        total_time = total_time_stats['mean']
        num_steps = partition['step_by_step_timing']['total_steps']
        avg_step = total_time / num_steps if num_steps > 0 else 0
        
        # Check if multiple runs were performed
        num_runs = partition['step_by_step_timing'].get('num_runs', 1)
        if num_runs > 1:
            print(f"  {partition_name:8s}: {num_steps:2d} steps | "
                  f"Batch: {batch_time:.3f}s | "
                  f"Total: {total_time:.3f}s (±{total_time_stats['std']:.3f}s, {num_runs} runs) | "
                  f"Avg/step: {avg_step:.3f}s")
        else:
            print(f"  {partition_name:8s}: {num_steps:2d} steps | "
                  f"Batch: {batch_time:.3f}s | "
                  f"Total: {total_time:.3f}s | "
              f"Avg/step: {avg_step:.4f}s")


def main():
    parser = argparse.ArgumentParser(
        description='Plot step-by-step timing results from partition enforcement',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('json_file', 
                       help='Path to partition_enforcement_results.json')
    parser.add_argument('-o', '--output', 
                       help='Output file path (PNG, PDF, SVG, etc.). If not specified, shows interactive plot.')
    
    args = parser.parse_args()
    
    if not Path(args.json_file).exists():
        print(f"Error: File not found: {args.json_file}")
        return 1
    
    plot_step_by_step_timing(args.json_file, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
