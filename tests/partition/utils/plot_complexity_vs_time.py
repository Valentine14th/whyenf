#!/usr/bin/env python3
"""
Plot partition complexity vs execution time.
Shows how number of rules and LETs correlate with enforcement time.
"""

import argparse
import json
import matplotlib.pyplot as plt
import numpy as np
import re
from pathlib import Path


def count_mfotl_elements(mfotl_file: str):
    """
    Count LETs and rules in an MFOTL file.
    
    Args:
        mfotl_file: Path to MFOTL file
        
    Returns:
        Tuple of (num_lets, num_rules)
    """
    with open(mfotl_file, 'r') as f:
        content = f.read()
    
    # Count LET statements (lines starting with "LET ")
    num_lets = len(re.findall(r'^LET\s+', content, re.MULTILINE))
    
    # Count rules: □[ can appear at start of line or after ∧:R or ∧:L
    # Match both "□[" at line start and after conjunctions
    num_rules = len(re.findall(r'□\[', content))
    
    return num_lets, num_rules


def plot_complexity_vs_time(json_file: str, mfotl_dir: str, output_file: str = None):
    """
    Plot partition complexity (rules and LETs) vs execution time.
    
    Args:
        json_file: Path to partition_enforcement_results.json
        mfotl_dir: Directory containing partition MFOTL files
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
    
    print(f"Analyzing {len(partitions)} partitions")
    
    # Collect data for plotting
    partition_names = []
    num_rules_list = []
    num_lets_list = []
    batch_times = []
    batch_stds = []
    total_times = []
    
    for partition in partitions:
        partition_file = partition['file']
        partition_name = partition_file.replace('minitwit_gdpr_4_partition_', 'P').replace('.mfotl', '')
        
        # Get timing data
        batch_time = partition['time_stats']['mean']
        batch_std = partition['time_stats']['std']
        
        # Check if step-by-step timing exists and was successful
        has_step_timing = (partition.get('step_by_step_timing') is not None and 
                          partition.get('step_by_step_timing', {}).get('status') == 'success')
        total_time = partition['step_by_step_timing']['total_time_stats']['mean'] if has_step_timing else None
        
        # Find and analyze MFOTL file
        mfotl_path = Path(mfotl_dir) / partition_file
        
        if not mfotl_path.exists():
            print(f"Warning: MFOTL file not found: {mfotl_path}")
            continue
        
        num_lets, num_rules = count_mfotl_elements(str(mfotl_path))
        
        print(f"  {partition_name:8s}: {num_rules:2d} rules, {num_lets:2d} LETs | "
              f"Batch: {batch_time:.3f}s")
        
        partition_names.append(partition_name)
        num_rules_list.append(num_rules)
        num_lets_list.append(num_lets)
        batch_times.append(batch_time)
        batch_stds.append(batch_std)
        if total_time is not None:
            total_times.append(total_time)
    
    if not partition_names:
        print("No valid partition data to plot")
        return
    
    # Use batch time (standard execution time)
    times_to_plot = batch_times
    time_label = "Batch Time (s)"
    
    # Create figure with two subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Number of Rules vs Time
    # Add error bars if standard deviation data is available
    has_variance = any(std > 0 for std in batch_stds)
    if has_variance:
        ax1.errorbar(num_rules_list, times_to_plot, yerr=batch_stds,
                    fmt='o', markersize=8, alpha=0.6, color='steelblue', 
                    ecolor='gray', elinewidth=2, capsize=4, capthick=2,
                    markeredgecolor='black', markeredgewidth=1.5)
    else:
        ax1.scatter(num_rules_list, times_to_plot, s=100, alpha=0.6, color='steelblue', 
                   edgecolors='black', linewidth=1.5)
    
    # Add partition labels to each point
    for i, name in enumerate(partition_names):
        ax1.annotate(name, (num_rules_list[i], times_to_plot[i]), 
                    textcoords="offset points", xytext=(5, 5), 
                    fontsize=9, alpha=0.8)
    
    # Add trend line for rules
    if len(num_rules_list) > 1 and len(set(num_rules_list)) > 1:
        z = np.polyfit(num_rules_list, times_to_plot, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(num_rules_list), max(num_rules_list), 100)
        ax1.plot(x_trend, p(x_trend), "r--", alpha=0.5, linewidth=2, label=f'Trend: y={z[0]:.3f}x+{z[1]:.3f}')
        ax1.legend(fontsize=10)
    
    ax1.set_xlabel('Number of Rules', fontsize=12, fontweight='bold')
    ax1.set_ylabel(time_label, fontsize=12, fontweight='bold')
    title1 = 'Enforcement Time vs Number of Rules'
    if has_variance:
        title1 += ' (error bars: ±1 std dev)'
    ax1.set_title(title1, fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Number of LETs vs Time
    # Add error bars if standard deviation data is available
    if has_variance:
        ax2.errorbar(num_lets_list, times_to_plot, yerr=batch_stds,
                    fmt='o', markersize=8, alpha=0.6, color='darkorange', 
                    ecolor='gray', elinewidth=2, capsize=4, capthick=2,
                    markeredgecolor='black', markeredgewidth=1.5)
    else:
        ax2.scatter(num_lets_list, times_to_plot, s=100, alpha=0.6, color='darkorange', 
                   edgecolors='black', linewidth=1.5)
    
    # Add partition labels to each point
    for i, name in enumerate(partition_names):
        ax2.annotate(name, (num_lets_list[i], times_to_plot[i]), 
                    textcoords="offset points", xytext=(5, 5), 
                    fontsize=9, alpha=0.8)
    
    # Add trend line for LETs
    if len(num_lets_list) > 1:
        z = np.polyfit(num_lets_list, times_to_plot, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(num_lets_list), max(num_lets_list), 100)
        ax2.plot(x_trend, p(x_trend), "r--", alpha=0.5, linewidth=2, label=f'Trend: y={z[0]:.3f}x+{z[1]:.3f}')
        ax2.legend(fontsize=10)
    
    ax2.set_xlabel('Number of LETs', fontsize=12, fontweight='bold')
    ax2.set_ylabel(time_label, fontsize=12, fontweight='bold')
    title2 = 'Enforcement Time vs Number of LETs'
    if has_variance:
        title2 += ' (error bars: ±1 std dev)'
    ax2.set_title(title2, fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\nPlot saved to: {output_file}")
    else:
        plt.show()
    
    # Print correlation statistics
    print("\n=== Correlation Analysis ===")
    
    if len(num_rules_list) > 1:
        if len(set(num_rules_list)) > 1:
            corr_rules = np.corrcoef(num_rules_list, times_to_plot)[0, 1]
            print(f"Rules vs Time correlation: {corr_rules:.3f}")
        else:
            print(f"Rules vs Time correlation: N/A (all partitions have same number of rules)")
    
    if len(num_lets_list) > 1:
        if len(set(num_lets_list)) > 1:
            corr_lets = np.corrcoef(num_lets_list, times_to_plot)[0, 1]
            print(f"LETs vs Time correlation: {corr_lets:.3f}")
        else:
            print(f"LETs vs Time correlation: N/A (all partitions have same number of LETs)")


def main():
    parser = argparse.ArgumentParser(
        description='Plot partition complexity (rules & LETs) vs execution time',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('json_file', 
                       help='Path to partition_enforcement_results.json')
    parser.add_argument('mfotl_dir',
                       help='Directory containing partition MFOTL files')
    parser.add_argument('-o', '--output', 
                       help='Output file path (PNG, PDF, SVG, etc.). If not specified, shows interactive plot.')
    
    args = parser.parse_args()
    
    if not Path(args.json_file).exists():
        print(f"Error: File not found: {args.json_file}")
        return 1
    
    if not Path(args.mfotl_dir).is_dir():
        print(f"Error: Directory not found: {args.mfotl_dir}")
        return 1
    
    plot_complexity_vs_time(args.json_file, args.mfotl_dir, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
