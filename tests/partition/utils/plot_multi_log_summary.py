#!/usr/bin/env python3
"""
Generate summary plots across all log files.
Creates three visualizations:
1. Log matching status and failures summary
2. Speedup comparison (slowest partition vs reference) for each log
3. Complexity vs time across all logs
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
    num_rules = len(re.findall(r'□\[', content))
    
    return num_lets, num_rules


def plot_matching_and_failures(summary_data: dict, output_file: str = None):
    """
    Plot 1: Summary of matching status and failures across all logs.
    
    Args:
        summary_data: Multi-log summary JSON data
        output_file: Optional path to save the plot
    """
    log_results = summary_data['log_results']
    
    # Count logs by matching status
    fully_matching = 0  # Combined partitions match reference
    not_matching = 0  # Combined partitions don't match reference
    has_failures = 0  # At least one partition failed
    
    log_names = []
    matching_statuses = []
    match_percentages = []
    
    for log_result in log_results:
        log_name = log_result['log_file'].replace('.log', '').replace('minitwit_', '')
        log_names.append(log_name)
        
        summary = log_result['enforcement_summary']
        failed_count = summary['status_counts']['failed']
        
        if failed_count > 0:
            has_failures += 1
            matching_statuses.append('failed')
            match_percentages.append(0)
        elif summary.get('combined_output_comparison') is None:
            # Reference enforcement failed or no comparison available
            matching_statuses.append('no_comparison')
            match_percentages.append(0)
        else:
            combined_comp = summary['combined_output_comparison']
            combined_matches = combined_comp.get('combined_matches', False)
            match_pct = combined_comp.get('combined_match_percentage', 0)
            match_percentages.append(match_pct)
            
            if combined_matches:
                fully_matching += 1
                matching_statuses.append('fully_matching')
            else:
                not_matching += 1
                matching_statuses.append('not_matching')
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1a: Pie chart of matching status
    labels = ['Combined Matches Reference', 'Combined Does Not Match', 'Has Failures']
    sizes = [fully_matching, not_matching, has_failures]
    colors = ['#2ecc71', '#e74c3c', '#95a5a6']
    explode = (0.05, 0, 0.1)  # Highlight fully matching and failures
    
    # Filter out zero values
    labels_filtered = [label for label, size in zip(labels, sizes) if size > 0]
    sizes_filtered = [size for size in sizes if size > 0]
    colors_filtered = [color for color, size in zip(colors, sizes) if size > 0]
    explode_filtered = [exp for exp, size in zip(explode, sizes) if size > 0]
    
    ax1.pie(sizes_filtered, explode=explode_filtered, labels=labels_filtered, colors=colors_filtered,
            autopct='%1.1f%%', shadow=True, startangle=90, textprops={'fontsize': 11, 'fontweight': 'bold'})
    ax1.set_title(f'Combined Partition Matching Status\n({len(log_results)} total logs)', 
                  fontsize=13, fontweight='bold')
    
    # Plot 1b: Bar chart per log showing match percentage
    color_map = {
        'fully_matching': '#2ecc71',
        'not_matching': '#e74c3c',
        'failed': '#95a5a6',
        'no_comparison': '#bdc3c7'
    }
    
    bar_colors = [color_map[status] for status in matching_statuses]
    
    y_pos = np.arange(len(log_names))
    bars = ax2.barh(y_pos, [100] * len(log_names), color=bar_colors, edgecolor='black', linewidth=1.2, alpha=0.3)
    bars_pct = ax2.barh(y_pos, match_percentages, color=bar_colors, edgecolor='black', linewidth=1.2)
    
    # Add percentage labels
    for i, (pct, status) in enumerate(zip(match_percentages, matching_statuses)):
        if status not in ['failed', 'no_comparison']:
            ax2.text(pct + 1, i, f'{pct:.1f}%', va='center', fontsize=8, fontweight='bold')
    
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(log_names, fontsize=9)
    ax2.set_xlim(0, 100)
    ax2.set_xlabel('Match Percentage (%)', fontsize=10, fontweight='bold')
    ax2.set_title('Combined Output Match Percentage per Log', fontsize=13, fontweight='bold')
    ax2.invert_yaxis()
    ax2.grid(axis='x', alpha=0.3)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', edgecolor='black', label='Fully Matching (100%)'),
        Patch(facecolor='#e74c3c', edgecolor='black', label='Not Matching'),
        Patch(facecolor='#95a5a6', edgecolor='black', label='Has Failures'),
        Patch(facecolor='#bdc3c7', edgecolor='black', label='No Comparison')
    ]
    ax2.legend(handles=legend_elements, loc='lower right', fontsize=9)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot 1 saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()


def plot_speedup_comparison(summary_data: dict, results_dir: Path = None, output_file: str = None):
    """
    Plot 2: Speedup between slowest partition and reference for each log.
    
    Args:
        summary_data: Multi-log summary JSON data
        results_dir: Optional base directory for loading detailed enforcement results
        output_file: Optional path to save the plot
    """
    log_results = summary_data['log_results']
    
    log_names = []
    speedups = []
    speedups_accumulated = []
    slowest_times = []
    reference_times = []
    accumulated_worst_case_times = []
    accumulated_step_contributors = []  # Track which partitions contributed to each step
    
    for log_result in log_results:
        log_name = log_result['log_file'].replace('.log', '').replace('minitwit_', '')
        summary = log_result['enforcement_summary']
        
        timing = summary.get('timing')
        if timing and 'reference_comparison' in timing:
            ref_comparison = timing['reference_comparison']
            speedup = ref_comparison.get('speedup')
            
            if speedup:
                log_names.append(log_name)
                reference_times.append(ref_comparison['reference_time'])
                
                # Calculate accumulated worst-case per-step time if step-by-step data available
                accumulated_time = None
                slowest_step_based_time = None
                speedup_for_slowest = speedup  # Default to batch-based speedup from JSON
                contributors = None  # Track which partitions contributed to accumulated worst-case
                
                if results_dir:
                    output_subdir = log_result['output_subdir']
                    enforcement_file = results_dir / output_subdir / 'enforcement_results.json'
                    
                    if enforcement_file.exists():
                        try:
                            with open(enforcement_file, 'r') as f:
                                enforcement_data = json.load(f)
                            
                            # Collect step timings from all successful partitions
                            step_max_times = {}  # step_number -> (max_time, partition_file)
                            partition_step_totals = []  # Total time from step-by-step for each partition
                            
                            for partition in enforcement_data.get('partition_details', []):
                                if partition['status'] != '✓ SUCCESS':
                                    continue
                                
                                partition_file = partition['file']
                                step_timing = partition.get('step_by_step_timing')
                                if step_timing and step_timing.get('status') == 'success':
                                    # Use step-by-step total time if available
                                    total_time_stats = step_timing.get('total_time_stats')
                                    if total_time_stats:
                                        partition_step_totals.append(total_time_stats['mean'])
                                    
                                    for step in step_timing.get('steps', []):
                                        step_num = step['step_number']
                                        step_time = step['step_time_stats']['mean']
                                        
                                        if step_num not in step_max_times:
                                            step_max_times[step_num] = (step_time, partition_file)
                                        else:
                                            # Update if this partition has a slower time for this step
                                            if step_time > step_max_times[step_num][0]:
                                                step_max_times[step_num] = (step_time, partition_file)
                            
                            # Sum up the max times across all steps and track contributors
                            if step_max_times:
                                accumulated_time = sum(time for time, _ in step_max_times.values())
                                # Create a summary of which partitions contributed
                                contributors = {}
                                for step_num, (step_time, part_file) in sorted(step_max_times.items()):
                                    # Simplify partition name
                                    part_name = part_file.replace('mfotl_', '').replace('.mfotl', '')
                                    if part_name not in contributors:
                                        contributors[part_name] = []
                                    contributors[part_name].append(step_num)
                            
                            # Use slowest partition's step-based total time if available
                            if partition_step_totals:
                                slowest_step_based_time = max(partition_step_totals)
                        except Exception as e:
                            print(f"Warning: Could not load step-by-step timing for {log_name}: {e}")
                
                # Use step-based time if available, otherwise use partition-level time
                if slowest_step_based_time is not None:
                    slowest_times.append(slowest_step_based_time)
                    # Recalculate speedup using step-based time
                    speedup_for_slowest = ref_comparison['reference_time'] / slowest_step_based_time
                else:
                    slowest_times.append(timing['max_time'])
                    # Keep batch-based speedup from JSON
                
                # Append the recalculated or original speedup
                speedups.append(speedup_for_slowest)
                
                accumulated_worst_case_times.append(accumulated_time)
                accumulated_step_contributors.append(contributors)
                
                # Calculate speedup for accumulated worst-case time
                if accumulated_time is not None:
                    speedup_acc = ref_comparison['reference_time'] / accumulated_time
                    speedups_accumulated.append(speedup_acc)
                else:
                    speedups_accumulated.append(None)
    
    if not log_names:
        print("No speedup data available")
        return
    
    # Check if we have accumulated worst-case data
    has_accumulated_data = any(t is not None for t in accumulated_worst_case_times)
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6))
    
    # Plot 2a: Speedup bar chart - now includes accumulated worst-case if available
    y_pos = np.arange(len(log_names))
    
    if has_accumulated_data:
        # Plot both slowest partition and accumulated worst-case speedups
        width = 0.35
        
        speedups_plot = speedups
        speedups_acc_plot = [s if s is not None else 0 for s in speedups_accumulated]
        
        bars1 = ax1.barh(y_pos - width/2, speedups_plot, width, 
                        color='#3498db', edgecolor='black', linewidth=1.2,
                        label='Slowest Partition')
        bars2 = ax1.barh(y_pos + width/2, speedups_acc_plot, width,
                        color='#9b59b6', edgecolor='black', linewidth=1.2,
                        label='Accumulated Worst-Case Per Step')
        
        # Add speedup values on bars with color based on speedup value
        for i, (bar, speedup) in enumerate(zip(bars1, speedups)):
            width_val = bar.get_width()
            text_color = '#2ecc71' if speedup > 1 else '#e74c3c'
            ax1.text(width_val + 0.05, bar.get_y() + bar.get_height()/2, 
                    f'{speedup:.2f}x', 
                    ha='left', va='center', fontsize=8, fontweight='bold',
                    color=text_color)
        
        for i, (bar, speedup) in enumerate(zip(bars2, speedups_accumulated)):
            if speedup is not None:
                width_val = bar.get_width()
                text_color = '#2ecc71' if speedup > 1 else '#e74c3c'
                ax1.text(width_val + 0.05, bar.get_y() + bar.get_height()/2, 
                        f'{speedup:.2f}x', 
                        ha='left', va='center', fontsize=8, fontweight='bold',
                        color=text_color)
        
        ax1.legend(fontsize=10, loc='lower right')
    else:
        # Original behavior - just slowest partition
        bars = ax1.barh(y_pos, speedups, color='#3498db', edgecolor='black', linewidth=1.2,
                       label='Slowest Partition')
        
        # Add speedup values on bars with color based on speedup value
        for i, (bar, speedup) in enumerate(zip(bars, speedups)):
            width_val = bar.get_width()
            text_color = '#2ecc71' if speedup > 1 else '#e74c3c'
            ax1.text(width_val + 0.05, bar.get_y() + bar.get_height()/2, 
                    f'{speedup:.2f}x', 
                    ha='left', va='center', fontsize=9, fontweight='bold',
                    color=text_color)
        
        ax1.legend(fontsize=10, loc='lower right')
    
    ax1.axvline(x=1, color='black', linestyle='--', linewidth=2, label='No speedup (1x)')
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(log_names, fontsize=9)
    ax1.set_xlabel('Speedup Factor (reference time / partition time)', fontsize=11, fontweight='bold')
    title = 'Speedup vs Reference'
    if has_accumulated_data:
        title += '\n(Slowest Partition & Accumulated Worst-Case)'
    ax1.set_title(title, fontsize=13, fontweight='bold')
    ax1.invert_yaxis()
    ax1.grid(axis='x', alpha=0.3)
    
    # Plot 2b: Time comparison (slowest partition vs reference vs accumulated worst-case)
    x = np.arange(len(log_names))
    
    if has_accumulated_data:
        # Three bars: slowest partition, accumulated worst-case, reference
        width = 0.25
        bars1 = ax2.bar(x - width, slowest_times, width, label='Slowest Partition', 
                        color='#3498db', edgecolor='black', linewidth=1.2)
        
        # Only plot accumulated bars where data is available
        acc_times_plot = [t if t is not None else 0 for t in accumulated_worst_case_times]
        bars2 = ax2.bar(x, acc_times_plot, width, label='Accumulated Worst-Case Per Step', 
                        color='#9b59b6', edgecolor='black', linewidth=1.2)
        
        bars3 = ax2.bar(x + width, reference_times, width, label='Reference', 
                        color='#e67e22', edgecolor='black', linewidth=1.2)
    else:
        # Two bars: slowest partition and reference (original behavior)
        width = 0.35
        bars1 = ax2.bar(x - width/2, slowest_times, width, label='Slowest Partition', 
                        color='#3498db', edgecolor='black', linewidth=1.2)
        bars3 = ax2.bar(x + width/2, reference_times, width, label='Reference', 
                        color='#e67e22', edgecolor='black', linewidth=1.2)
    
    ax2.set_xlabel('Log File', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Time (seconds)', fontsize=11, fontweight='bold')
    title = 'Execution Time Comparison'
    ax2.set_title(title, fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(log_names, rotation=45, ha='right', fontsize=9)
    ax2.legend(fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot 2 saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()
    
    # Print statistics
    print("\n=== Speedup Statistics (Slowest Partition) ===")
    print(f"Average speedup: {np.mean(speedups):.2f}x")
    print(f"Median speedup: {np.median(speedups):.2f}x")
    print(f"Min speedup: {np.min(speedups):.2f}x ({log_names[np.argmin(speedups)]})")
    print(f"Max speedup: {np.max(speedups):.2f}x ({log_names[np.argmax(speedups)]})")
    
    if has_accumulated_data:
        valid_speedups_acc = [s for s in speedups_accumulated if s is not None]
        if valid_speedups_acc:
            print("\n=== Speedup Statistics (Accumulated Worst-Case Per Step) ===")
            print(f"Average speedup: {np.mean(valid_speedups_acc):.2f}x")
            print(f"Median speedup: {np.median(valid_speedups_acc):.2f}x")
            print(f"Min speedup: {np.min(valid_speedups_acc):.2f}x")
            print(f"Max speedup: {np.max(valid_speedups_acc):.2f}x")
            
            # Show comparison
            print("\n=== Time Comparison ===")
            for i, log_name in enumerate(log_names):
                if accumulated_worst_case_times[i] is not None:
                    print(f"{log_name}:")
                    print(f"  Slowest partition: {slowest_times[i]:.2f}s")
                    print(f"  Accumulated worst-case: {accumulated_worst_case_times[i]:.2f}s")
                    print(f"  Reference: {reference_times[i]:.2f}s")
                    ratio = accumulated_worst_case_times[i] / slowest_times[i]
                    print(f"  Ratio (accumulated/slowest): {ratio:.2f}x")
                    
                    # Show which partitions contributed to accumulated worst-case
                    if accumulated_step_contributors[i] is not None:
                        contrib = accumulated_step_contributors[i]
                        # Format as: partition_name (steps X, Y, Z)
                        contrib_strs = [f"{part} (steps {', '.join(map(str, steps))})" 
                                       for part, steps in sorted(contrib.items())]
                        print(f"  Contributors: {'; '.join(contrib_strs)}")


def plot_complexity_vs_time_all_logs(summary_data: dict, results_dir: Path, 
                                      mfotl_dir: Path, output_file: str = None):
    """
    Plot 3: Complexity vs time across all logs and all partitions.
    
    Args:
        summary_data: Multi-log summary JSON data
        results_dir: Base directory containing all log subdirectories
        mfotl_dir: Directory containing partition MFOTL files
        output_file: Optional path to save the plot
    """
    log_results = summary_data['log_results']
    
    # Collect data from all partitions across all logs
    partition_data = []
    
    for log_result in log_results:
        log_name = log_result['log_file'].replace('.log', '').replace('minitwit_', '')
        output_subdir = log_result['output_subdir']
        
        # Load enforcement results for this log
        enforcement_file = results_dir / output_subdir / 'enforcement_results.json'
        
        if not enforcement_file.exists():
            print(f"Warning: enforcement results not found for {log_name}")
            continue
        
        with open(enforcement_file, 'r') as f:
            enforcement_data = json.load(f)
        
        # Process each partition
        for partition in enforcement_data.get('partition_details', []):
            if partition['status'] != '✓ SUCCESS':
                continue
            
            partition_file = partition['file']
            
            # Find and analyze MFOTL file
            mfotl_path = mfotl_dir / partition_file
            
            if not mfotl_path.exists():
                # Try alternate naming: mfotl_XXXX.mfotl -> minitwit_gdpr_4_partition_XXXX.mfotl
                alt_name = partition_file.replace('mfotl_', 'minitwit_gdpr_4_partition_')
                mfotl_path = mfotl_dir / alt_name
                
                if not mfotl_path.exists():
                    print(f"Warning: MFOTL file not found: {partition_file}")
                    continue
            
            num_lets, num_rules = count_mfotl_elements(str(mfotl_path))
            
            partition_data.append({
                'log': log_name,
                'partition': partition_file,
                'num_rules': num_rules,
                'num_lets': num_lets,
                'time': partition['time_stats']['mean'],
                'time_std': partition['time_stats']['std'],
                'match_percentage': partition.get('match_percentage', 100.0)
            })
    
    if not partition_data:
        print("No partition data to plot")
        return
    
    print(f"\nAnalyzing {len(partition_data)} partitions across {len(log_results)} logs")
    
    # Extract data for plotting
    num_rules_list = [p['num_rules'] for p in partition_data]
    num_lets_list = [p['num_lets'] for p in partition_data]
    times_list = [p['time'] for p in partition_data]
    times_std_list = [p['time_std'] for p in partition_data]
    
    # Check if any partition has variance (std > 0)
    has_variance = any(std > 0 for std in times_std_list)
    
    # Create color map based on log
    unique_logs = sorted(set(p['log'] for p in partition_data))
    color_map = plt.colormaps.get_cmap('tab20').resampled(len(unique_logs))
    log_colors = {log: color_map(i) for i, log in enumerate(unique_logs)}
    colors = [log_colors[p['log']] for p in partition_data]
    
    # Create figure with two subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    
    # Plot 3a: Number of Rules vs Time
    if has_variance:
        # Use errorbar plot with color-coded points
        for log in unique_logs:
            log_indices = [i for i, p in enumerate(partition_data) if p['log'] == log]
            log_rules = [num_rules_list[i] for i in log_indices]
            log_times = [times_list[i] for i in log_indices]
            log_stds = [times_std_list[i] for i in log_indices]
            ax1.errorbar(log_rules, log_times, yerr=log_stds,
                        fmt='o', markersize=6, alpha=0.6, color=log_colors[log],
                        ecolor='gray', elinewidth=1, capsize=3, capthick=1,
                        markeredgecolor='black', markeredgewidth=0.8)
    else:
        scatter1 = ax1.scatter(num_rules_list, times_list, s=80, alpha=0.6, 
                              c=colors, edgecolors='black', linewidth=0.8)
    
    # Add trend line for rules
    if len(num_rules_list) > 1 and len(set(num_rules_list)) > 1:
        z = np.polyfit(num_rules_list, times_list, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(num_rules_list), max(num_rules_list), 100)
        ax1.plot(x_trend, p(x_trend), "r--", alpha=0.7, linewidth=2.5, 
                label=f'Trend: y={z[0]:.3f}x+{z[1]:.3f}')
        ax1.legend(fontsize=11)
    
    ax1.set_xlabel('Number of Rules', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
    title1 = 'Enforcement Time vs Number of Rules\n(All Logs, All Partitions)'
    if has_variance:
        title1 += '\n(error bars: ±1 std dev)'
    ax1.set_title(title1, fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Plot 3b: Number of LETs vs Time
    if has_variance:
        # Use errorbar plot with color-coded points
        for log in unique_logs:
            log_indices = [i for i, p in enumerate(partition_data) if p['log'] == log]
            log_lets = [num_lets_list[i] for i in log_indices]
            log_times = [times_list[i] for i in log_indices]
            log_stds = [times_std_list[i] for i in log_indices]
            ax2.errorbar(log_lets, log_times, yerr=log_stds,
                        fmt='o', markersize=6, alpha=0.6, color=log_colors[log],
                        ecolor='gray', elinewidth=1, capsize=3, capthick=1,
                        markeredgecolor='black', markeredgewidth=0.8)
    else:
        scatter2 = ax2.scatter(num_lets_list, times_list, s=80, alpha=0.6, 
                              c=colors, edgecolors='black', linewidth=0.8)
    
    # Add trend line for LETs
    if len(num_lets_list) > 1 and len(set(num_lets_list)) > 1:
        z = np.polyfit(num_lets_list, times_list, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(num_lets_list), max(num_lets_list), 100)
        ax2.plot(x_trend, p(x_trend), "r--", alpha=0.7, linewidth=2.5, 
                label=f'Trend: y={z[0]:.3f}x+{z[1]:.3f}')
        ax2.legend(fontsize=11)
    
    ax2.set_xlabel('Number of LETs', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
    title2 = 'Enforcement Time vs Number of LETs\n(All Logs, All Partitions)'
    if has_variance:
        title2 += '\n(error bars: ±1 std dev)'
    ax2.set_title(title2, fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Add legend for logs (sample of logs if too many)
    if len(unique_logs) <= 10:
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=log_colors[log], edgecolor='black', label=log) 
                          for log in unique_logs]
        fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.02),
                  ncol=min(5, len(unique_logs)), fontsize=9, frameon=True)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot 3 saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()
    
    # Print correlation statistics
    print("\n=== Correlation Analysis (All Logs) ===")
    
    if len(num_rules_list) > 1 and len(set(num_rules_list)) > 1:
        corr_rules = np.corrcoef(num_rules_list, times_list)[0, 1]
        print(f"Rules vs Time correlation: {corr_rules:.3f}")
    else:
        print("Rules vs Time correlation: N/A (insufficient variation)")
    
    if len(num_lets_list) > 1 and len(set(num_lets_list)) > 1:
        corr_lets = np.corrcoef(num_lets_list, times_list)[0, 1]
        print(f"LETs vs Time correlation: {corr_lets:.3f}")
    else:
        print("LETs vs Time correlation: N/A (insufficient variation)")


def main():
    parser = argparse.ArgumentParser(
        description='Generate summary plots across all log files',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('summary_file', 
                       help='Path to multi_log_summary.json')
    parser.add_argument('results_dir',
                       help='Base directory containing log subdirectories')
    parser.add_argument('mfotl_dir',
                       help='Directory containing partition MFOTL files')
    parser.add_argument('-o', '--output-prefix', 
                       help='Output file prefix (will create 3 files: prefix_1.png, prefix_2.png, prefix_3.png)')
    
    args = parser.parse_args()
    
    summary_path = Path(args.summary_file)
    results_dir = Path(args.results_dir)
    mfotl_dir = Path(args.mfotl_dir)
    
    if not summary_path.exists():
        print(f"Error: File not found: {summary_path}")
        return 1
    
    if not results_dir.is_dir():
        print(f"Error: Directory not found: {results_dir}")
        return 1
    
    if not mfotl_dir.is_dir():
        print(f"Error: Directory not found: {mfotl_dir}")
        return 1
    
    # Load summary data
    with open(summary_path, 'r') as f:
        summary_data = json.load(f)
    
    print(f"Processing {summary_data['total_logs']} logs from {summary_data['workflow_name']}")
    
    # Determine output file names
    if args.output_prefix:
        output_1 = f"{args.output_prefix}_matching_status.png"
        output_2 = f"{args.output_prefix}_speedup.png"
        output_3 = f"{args.output_prefix}_complexity_vs_time.png"
    else:
        output_1 = output_2 = output_3 = None
    
    # Generate plots
    print("\n=== Generating Plot 1: Matching Status and Failures ===")
    plot_matching_and_failures(summary_data, output_1)
    
    print("\n=== Generating Plot 2: Speedup Comparison ===")
    plot_speedup_comparison(summary_data, results_dir, output_2)
    
    print("\n=== Generating Plot 3: Complexity vs Time (All Logs) ===")
    plot_complexity_vs_time_all_logs(summary_data, results_dir, mfotl_dir, output_3)
    
    print("\n✓ All plots generated successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
