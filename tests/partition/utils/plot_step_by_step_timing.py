#!/usr/bin/env python3
"""
Plot step-by-step timing results from partition enforcement.
Shows runtime per step for each partition with reference lines for batch and total time.
"""

import argparse
import json
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from pathlib import Path


def detect_outliers(values, method='iqr', threshold=3.0):
    """
    Detect outliers in a list of values.
    
    Args:
        values: List of numeric values
        method: 'iqr' (Interquartile Range) or 'zscore'
        threshold: For IQR method, multiplier for IQR (default 3.0 for extreme outliers)
                   For zscore method, number of standard deviations (default 3.0)
    
    Returns:
        List of booleans indicating whether each value is an outlier
    """
    if len(values) < 4:
        # Not enough data to detect outliers
        return [False] * len(values)
    
    values_array = np.array(values)
    
    if method == 'iqr':
        q1 = np.percentile(values_array, 25)
        q3 = np.percentile(values_array, 75)
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        outliers = (values_array < lower_bound) | (values_array > upper_bound)
    else:  # zscore
        mean = np.mean(values_array)
        std = np.std(values_array)
        if std == 0:
            return [False] * len(values)
        z_scores = np.abs((values_array - mean) / std)
        outliers = z_scores > threshold
    
    return outliers.tolist()


def filter_outliers_within_step_runs(step):
    """
    Filter outlier runs within a single step and recalculate statistics.
    
    Args:
        step: Step dictionary with 'step_time_stats' containing 'runs'
    
    Returns:
        Tuple of (filtered_step_stats, num_outliers_removed)
        - filtered_step_stats: Updated stats dict with outliers removed
        - num_outliers_removed: Number of runs that were filtered out
    """
    step_time_stats = step.get('step_time_stats', {})
    runs = step_time_stats.get('runs', [])
    
    if not runs or len(runs) < 4:
        # Not enough runs to detect outliers, return original stats
        return step_time_stats, 0
    
    # Detect outliers within this step's runs
    outlier_mask = detect_outliers(runs, method='iqr', threshold=3.0)
    
    # Filter out outlier runs
    filtered_runs = [run for run, is_outlier in zip(runs, outlier_mask) if not is_outlier]
    num_outliers = sum(outlier_mask)
    
    # If all runs were outliers or none remain, return original
    if not filtered_runs:
        return step_time_stats, 0
    
    # Recalculate statistics with filtered runs
    filtered_stats = {
        'mean': np.mean(filtered_runs),
        'std': np.std(filtered_runs),
        'min': np.min(filtered_runs),
        'max': np.max(filtered_runs),
        'runs': filtered_runs
    }
    
    return filtered_stats, num_outliers


def plot_step_by_step_timing(json_file: str, output_file: str = None, partition_names: dict = None):
    """
    Plot step-by-step timing from enforcement results JSON.
    
    Args:
        json_file: Path to partition_enforcement_results.json
        output_file: Optional path to save the plot (default: show interactive plot)
        partition_names: Optional dict mapping partition filenames to custom display names
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
    
    # Extract reference timing if available
    reference_timing = None
    reference_batch_time = None
    if 'timing' in data and 'reference_comparison' in data['timing']:
        ref_comp = data['timing']['reference_comparison']
        if 'reference_time_stats' in ref_comp:
            ref_stats = ref_comp['reference_time_stats']
            if 'step_by_step_timing' in ref_stats:
                reference_timing = ref_stats['step_by_step_timing']
                reference_batch_time = ref_stats.get('mean')
    
    if not partitions_with_timing and not reference_timing:
        print("No step-by-step timing data found")
        return
    
    print(f"Plotting timing for {len(partitions_with_timing)} partitions" + 
          (f" + reference" if reference_timing else ""))
    
    # Determine total timepoints to decide whether to suppress per-point markers
    max_timepoints = max(
        (len(p['step_by_step_timing']['steps']) for p in partitions_with_timing),
        default=0
    )
    if reference_timing and reference_timing.get('steps'):
        max_timepoints = max(max_timepoints, len(reference_timing['steps']))
    MARKER_THRESHOLD = 50
    many_timepoints = max_timepoints > MARKER_THRESHOLD
    if many_timepoints:
        print(f"  Many timepoints ({max_timepoints} > {MARKER_THRESHOLD}): block-type markers suppressed")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Colors for different partitions
    colors = plt.cm.tab10(np.linspace(0, 1, len(partitions_with_timing)))
    
    # Track batch and interactive times for reference lines
    batch_times = []
    total_times = []
    
    # Track outlier run counts
    total_outlier_runs_removed = 0
    
    # Define marker styles for different block types
    marker_styles = {
        ('reactive', True): {'marker': 'o', 'label_suffix': ' (R+A)'},      # Reactive with action: circle
        ('reactive', False): {'marker': 'o', 'label_suffix': ' (R)',        # Reactive no action: circle (faded)
                             'facecolor': 'none'},
        ('proactive', True): {'marker': 's', 'label_suffix': ' (P+A)'},     # Proactive with action: square
        ('proactive', False): {'marker': 's', 'label_suffix': ' (P)',       # Proactive no action: square (faded)
                              'facecolor': 'none'}
    }
    
    # Plot each partition
    for idx, partition in enumerate(partitions_with_timing):
        partition_file = partition['file']
        # Use custom name if provided, otherwise use default naming
        if partition_names and partition_file in partition_names:
            partition_name = partition_names[partition_file]
        else:
            partition_name = partition_file.replace('minitwit_gdpr_4_partition_', 'P').replace('.mfotl', '')
        
        # Process all steps and filter outlier runs within each step
        original_steps = partition['step_by_step_timing']['steps']
        steps = []
        partition_outliers_removed = 0
        
        for step in original_steps:
            # Filter outliers within this step's runs
            filtered_stats, num_outliers = filter_outliers_within_step_runs(step)
            partition_outliers_removed += num_outliers
            
            # Create updated step with filtered stats
            updated_step = step.copy()
            updated_step['step_time_stats'] = filtered_stats
            steps.append(updated_step)
        
        if partition_outliers_removed > 0:
            print(f"  {partition_name}: Filtered {partition_outliers_removed} outlier run(s) across all steps")
            total_outlier_runs_removed += partition_outliers_removed
        
        # Skip if no steps available
        if not steps:
            print(f"  {partition_name}: Warning - no steps found, skipping partition")
            continue
        
        batch_time = partition['time_stats']['mean']
        total_time = partition['step_by_step_timing']['total_time_stats']['mean']
        
        batch_times.append(batch_time)
        total_times.append(total_time)
        
        # Extract timepoints, step times, timestamps, and block metadata
        timepoints = [s['timepoint'] for s in steps]
        step_times = [s['step_time_stats']['mean'] for s in steps]
        step_stds = [s['step_time_stats']['std'] for s in steps]
        timestamps = [s.get('timestamp', s['timepoint']) for s in steps]  # Fall back to timepoint if timestamp missing
        
        # Group points by block type for different markers
        block_groups = {}
        for s in steps:
            block_type = s.get('block_type', 'unknown')
            has_action = s.get('has_action', False)
            key = (block_type, has_action)
            if key not in block_groups:
                block_groups[key] = {'timepoints': [], 'times': [], 'stds': []}
            block_groups[key]['timepoints'].append(s['timepoint'])
            block_groups[key]['times'].append(s['step_time_stats']['mean'])
            block_groups[key]['stds'].append(s['step_time_stats']['std'])
        
        # Check if multiple runs were performed (std > 0 indicates repeated runs)
        num_runs = partition['step_by_step_timing'].get('num_runs', 1)
        has_variance = num_runs > 1 and any(std > 0 for std in step_stds)
        
        if not many_timepoints:
            # Plot single connecting line
            ax.plot(timepoints, step_times,
                    linewidth=1.5,
                    color=colors[idx],
                    alpha=0.8,
                    zorder=1)
            
            # Plot points with different markers based on block type
            for block_key, group_data in block_groups.items():
                style = marker_styles.get(block_key, {'marker': 'x'})
                marker = style.get('marker', 'x')
                facecolor = style.get('facecolor', colors[idx])
                
                # Only add label for first group to avoid legend clutter
                label = None
                if block_key == list(block_groups.keys())[0]:
                    label = partition_name
                
                ax.scatter(group_data['timepoints'], group_data['times'],
                          marker=marker, s=40,
                          facecolor=facecolor,
                          edgecolor=colors[idx],
                          linewidth=1.5,
                          label=label,
                          alpha=0.9,
                          zorder=2)
            
            if has_variance:
                step_times_array = np.array(step_times)
                step_stds_array = np.array(step_stds)
                ax.fill_between(timepoints,
                               step_times_array - step_stds_array,
                               step_times_array + step_stds_array,
                               color=colors[idx], alpha=0.2, zorder=0)
        else:
            # Split into separate lines per block type (reactive=solid, proactive=dotted)
            type_groups = {}
            for s in steps:
                bt = s.get('block_type', 'unknown')
                if bt not in type_groups:
                    type_groups[bt] = {'timepoints': [], 'times': [], 'stds': []}
                type_groups[bt]['timepoints'].append(s['timepoint'])
                type_groups[bt]['times'].append(s['step_time_stats']['mean'])
                type_groups[bt]['stds'].append(s['step_time_stats']['std'])
            
            type_linestyles = {'reactive': '-', 'proactive': ':'}
            for bt in sorted(type_groups.keys()):
                grp = type_groups[bt]
                ls = type_linestyles.get(bt, '--')
                ax.plot(grp['timepoints'], grp['times'],
                        linewidth=1.5,
                        color=colors[idx],
                        alpha=0.8,
                        linestyle=ls,
                        label=f"{partition_name} ({bt})",
                        zorder=1)
                if has_variance:
                    times_arr = np.array(grp['times'])
                    stds_arr = np.array(grp['stds'])
                    ax.fill_between(grp['timepoints'],
                                   times_arr - stds_arr,
                                   times_arr + stds_arr,
                                   color=colors[idx], alpha=0.2, zorder=0)
    
    # Plot reference timing if available
    if reference_timing and reference_timing.get('steps'):
        # Process all steps and filter outlier runs within each step
        original_steps = reference_timing['steps']
        steps = []
        reference_outliers_removed = 0
        
        for step in original_steps:
            # Filter outliers within this step's runs
            filtered_stats, num_outliers = filter_outliers_within_step_runs(step)
            reference_outliers_removed += num_outliers
            
            # Create updated step with filtered stats
            updated_step = step.copy()
            updated_step['step_time_stats'] = filtered_stats
            steps.append(updated_step)
        
        if reference_outliers_removed > 0:
            print(f"  Reference: Filtered {reference_outliers_removed} outlier run(s) across all steps")
            total_outlier_runs_removed += reference_outliers_removed
        
        # Skip if no steps available
        if not steps:
            print("  Reference: Warning - no steps found, skipping reference")
        else:
            timepoints = [s['timepoint'] for s in steps]
            step_times = [s['step_time_stats']['mean'] for s in steps]
            step_stds = [s['step_time_stats']['std'] for s in steps]
            timestamps = [s.get('timestamp', s['timepoint']) for s in steps]  # Fall back to timepoint if timestamp missing
            
            # Group points by block type for different markers
            block_groups = {}
            for s in steps:
                block_type = s.get('block_type', 'unknown')
                has_action = s.get('has_action', False)
                key = (block_type, has_action)
                if key not in block_groups:
                    block_groups[key] = {'timepoints': [], 'times': [], 'stds': []}
                block_groups[key]['timepoints'].append(s['timepoint'])
                block_groups[key]['times'].append(s['step_time_stats']['mean'])
                block_groups[key]['stds'].append(s['step_time_stats']['std'])
            
            num_runs = reference_timing.get('num_runs', 1)
            has_variance = num_runs > 1 and any(std > 0 for std in step_stds)
            
            if not many_timepoints:
                # Plot single connecting line (black dashed)
                ax.plot(timepoints, step_times,
                        linewidth=1.5,
                        linestyle='--',
                        color='black',
                        alpha=0.7,
                        zorder=10)
                
                # Plot points with different markers based on block type
                for block_key, group_data in block_groups.items():
                    style = marker_styles.get(block_key, {'marker': 'x'})
                    marker = style.get('marker', 'x')
                    facecolor = style.get('facecolor', 'black')
                    
                    label = None
                    if block_key == list(block_groups.keys())[0]:
                        label = 'Reference (full formula)'
                    
                    ax.scatter(group_data['timepoints'], group_data['times'],
                              marker=marker, s=40,
                              facecolor=facecolor,
                              edgecolor='black',
                              linewidth=1.5,
                              label=label,
                              alpha=0.8,
                              zorder=11)
                
                if has_variance:
                    step_times_array = np.array(step_times)
                    step_stds_array = np.array(step_stds)
                    ax.fill_between(timepoints,
                                   step_times_array - step_stds_array,
                                   step_times_array + step_stds_array,
                                   color='gray', alpha=0.2, zorder=9)
            else:
                # Split into separate lines per block type
                ref_type_groups = {}
                for s in steps:
                    bt = s.get('block_type', 'unknown')
                    if bt not in ref_type_groups:
                        ref_type_groups[bt] = {'timepoints': [], 'times': [], 'stds': []}
                    ref_type_groups[bt]['timepoints'].append(s['timepoint'])
                    ref_type_groups[bt]['times'].append(s['step_time_stats']['mean'])
                    ref_type_groups[bt]['stds'].append(s['step_time_stats']['std'])
                
                ref_type_linestyles = {'reactive': '--', 'proactive': ':'}
                for bt in sorted(ref_type_groups.keys()):
                    grp = ref_type_groups[bt]
                    ls = ref_type_linestyles.get(bt, '-.')
                    ax.plot(grp['timepoints'], grp['times'],
                            linewidth=1.5,
                            linestyle=ls,
                            color='black',
                            alpha=0.7,
                            label=f"Reference ({bt})",
                            zorder=10)
                    if has_variance:
                        times_arr = np.array(grp['times'])
                        stds_arr = np.array(grp['stds'])
                        ax.fill_between(grp['timepoints'],
                                       times_arr - stds_arr,
                                       times_arr + stds_arr,
                                       color='gray', alpha=0.2, zorder=9)
    
    # Calculate average times for summary stats (but don't plot them)
    avg_batch_time = np.mean(batch_times) if batch_times else 0
    avg_total_time = np.mean(total_times) if total_times else 0
    
    # Check if any partition has multiple runs
    any_multiple_runs = any(p['step_by_step_timing'].get('num_runs', 1) > 1 for p in partitions_with_timing)
    if reference_timing:
        any_multiple_runs = any_multiple_runs or reference_timing.get('num_runs', 1) > 1
    
    # Set x-axis labels with timepoints and timestamps
    # Get timepoints and timestamps from reference or first partition
    if reference_timing and reference_timing.get('steps'):
        x_data = {s['timepoint']: s.get('timestamp', s['timepoint']) for s in reference_timing['steps']}
    elif partitions_with_timing:
        x_data = {s['timepoint']: s.get('timestamp', s['timepoint']) for s in partitions_with_timing[0]['step_by_step_timing']['steps']}
    else:
        x_data = {}
    
    if x_data:
        # Set up x-axis with automatic integer tick spacing
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True, nbins='auto'))
        
        # Add secondary x-axis at top showing timestamps
        ax2 = ax.twiny()
        
        # Find positions where timestamp changes (boundaries)
        sorted_timepoints = sorted(x_data.keys())
        timestamp_positions = []
        timestamp_labels = []
        prev_timestamp = None
        
        for tp in sorted_timepoints:
            curr_timestamp = x_data[tp]
            if prev_timestamp is None or curr_timestamp != prev_timestamp:
                timestamp_positions.append(tp)
                timestamp_labels.append(str(curr_timestamp))
            prev_timestamp = curr_timestamp
        
        # Limit number of ticks if there are too many timestamp changes
        max_ticks = 15  # Maximum number of ticks to display
        if len(timestamp_positions) > max_ticks:
            # Select evenly spaced indices
            step = len(timestamp_positions) // max_ticks
            indices = list(range(0, len(timestamp_positions), step))
            # Always include the last timestamp
            if indices[-1] != len(timestamp_positions) - 1:
                indices.append(len(timestamp_positions) - 1)
            timestamp_positions = [timestamp_positions[i] for i in indices]
            timestamp_labels = [timestamp_labels[i] for i in indices]
        
        # Set up secondary axis with timestamp labels
        ax2.set_xlim(ax.get_xlim())
        ax2.set_xticks(timestamp_positions)
        ax2.set_xticklabels(timestamp_labels, rotation=45, ha='left', fontsize=9)
        ax2.set_xlabel('Timestamp', fontsize=12, fontweight='bold')
    
    # Formatting
    ax.set_xlabel('Timepoint', fontsize=12, fontweight='bold')
    ax.set_ylabel('Time (proactive+reactive) [seconds]', fontsize=12, fontweight='bold')
    title = 'Step-by-Step Enforcement Timing'
    if reference_timing:
        title += ' (Partitions vs Reference)'
    else:
        title += ' per Partition'
    if total_outlier_runs_removed > 0:
        title += f' ({total_outlier_runs_removed} outlier run(s) filtered)'
    if any_multiple_runs:
        title += ' (shaded regions show ±1 std dev)'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Create main legend for partitions
    main_legend = ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9, title='Partitions')
    ax.add_artist(main_legend)
    
    # Add block type legend below main legend
    if many_timepoints:
        block_type_legend_elements = [
            Line2D([0], [0], color='gray', linestyle='-', linewidth=1.5, label='Reactive'),
            Line2D([0], [0], color='gray', linestyle=':', linewidth=1.5, label='Proactive'),
        ]
        block_type_legend_title = 'Block Types (line style)'
    else:
        block_type_legend_elements = [
            Line2D([0], [0], marker='o', color='gray', linestyle='', markersize=8,
                   label='Reactive + Action', markerfacecolor='gray'),
            Line2D([0], [0], marker='o', color='gray', linestyle='', markersize=8,
                   label='Reactive + No Action', markerfacecolor='none', markeredgewidth=1.5),
            Line2D([0], [0], marker='s', color='gray', linestyle='', markersize=8,
                   label='Proactive + Action', markerfacecolor='gray'),
            Line2D([0], [0], marker='s', color='gray', linestyle='', markersize=8,
                   label='Proactive + No Action', markerfacecolor='none', markeredgewidth=1.5),
        ]
        block_type_legend_title = 'Block Types'
    ax.legend(handles=block_type_legend_elements, bbox_to_anchor=(1.05, 0.6),
             loc='upper left', fontsize=8, title=block_type_legend_title, framealpha=0.9)
    
    # Set y-axis to log scale if there's a large range
    step_times_all = [s['step_time_stats']['mean'] for p in partitions_with_timing for s in p['step_by_step_timing']['steps']]
    if reference_timing and reference_timing.get('steps'):
        step_times_all.extend([s['step_time_stats']['mean'] for s in reference_timing['steps']])
    if step_times_all and max(step_times_all) / min(step_times_all) > 100:
        ax.set_yscale('log')
        ax.set_ylabel('Time (proactive+reactive, log scale) [seconds]', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    else:
        plt.show()
    
    # Print summary statistics
    print("\n=== Timing Summary ===")
    if batch_times:
        print(f"Average Batch Time: {avg_batch_time:.3f}s")
        print(f"Average Total Time (step-by-step): {avg_total_time:.3f}s")
        print(f"Overhead: {avg_total_time - avg_batch_time:.3f}s ({((avg_total_time/avg_batch_time - 1) * 100):.1f}%)")
    
    # Per-partition summary
    if partitions_with_timing:
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
    
    # Print reference summary if available
    if reference_timing:
        print("\nReference Formula Details:")
        ref_total_time_stats = reference_timing['total_time_stats']
        ref_total_time = ref_total_time_stats['mean']
        ref_num_steps = reference_timing['total_steps']
        ref_avg_step = ref_total_time / ref_num_steps if ref_num_steps > 0 else 0
        ref_num_runs = reference_timing.get('num_runs', 1)
        
        if ref_num_runs > 1:
            print(f"  Reference: {ref_num_steps:2d} steps | "
                  f"Batch: {reference_batch_time:.3f}s | "
                  f"Total: {ref_total_time:.3f}s (±{ref_total_time_stats['std']:.3f}s, {ref_num_runs} runs) | "
                  f"Avg/step: {ref_avg_step:.3f}s")
        else:
            print(f"  Reference: {ref_num_steps:2d} steps | "
                  f"Batch: {reference_batch_time:.3f}s | "
                  f"Total: {ref_total_time:.3f}s | "
                  f"Avg/step: {ref_avg_step:.4f}s")


def main():
    parser = argparse.ArgumentParser(
        description='Plot step-by-step timing results from partition enforcement',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('json_file', 
                       help='Path to partition_enforcement_results.json')
    parser.add_argument('-o', '--output', 
                       help='Output file path (PNG, PDF, SVG, etc.). If not specified, shows interactive plot.')
    parser.add_argument('--partition-names', type=str,
                       help='JSON file with partition name mappings')
    
    args = parser.parse_args()
    
    # Load partition names if provided
    partition_names = None
    if args.partition_names:
        if not Path(args.partition_names).exists():
            print(f"Error: Partition names file not found: {args.partition_names}")
            return 1
        try:
            with open(args.partition_names, 'r') as f:
                partition_names = json.load(f)
        except Exception as e:
            print(f"Error loading partition names: {e}")
            return 1
    
    if not Path(args.json_file).exists():
        print(f"Error: File not found: {args.json_file}")
        return 1
    
    plot_step_by_step_timing(args.json_file, args.output, partition_names)
    return 0


if __name__ == "__main__":
    exit(main())
