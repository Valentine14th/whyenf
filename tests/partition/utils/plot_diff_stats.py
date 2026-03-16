#!/usr/bin/env python3
"""
Script to plot differences across partitions over time.
Creates 4 subplots for suppression/causation reactive/proactive differences.
"""

import json
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
import numpy as np

def load_diff_file(filepath):
    """Load a diff JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def count_differences(diff_block):
    """
    Count differences in a diff block, returning separate positive and negative components.
    Returns (extra, missing) for each category where:
    - extra (positive) = partition has MORE than reference (only_in_partition)
    - missing (negative) = partition has LESS than reference (only_in_reference)
    """
    diffs = diff_block.get('differences', {})
    
    # Count causation differences (separate components)
    causes_missing = -len(diffs.get('causes', {}).get('only_in_reference', []))  # Missing from partition (negative)
    causes_extra = len(diffs.get('causes', {}).get('only_in_partition', []))  # Extra in partition (positive)
    
    # Count suppression differences (separate components)
    supp_missing = -len(diffs.get('suppressions', {}).get('only_in_reference', []))  # Missing from partition (negative)
    supp_extra = len(diffs.get('suppressions', {}).get('only_in_partition', []))  # Extra in partition (positive)
    
    return (causes_extra, causes_missing), (supp_extra, supp_missing)

def extract_partition_data(diff_data):
    """
    Extract time-series data for a partition.
    Returns separate dictionaries for extra (positive) and missing (negative) components.
    """
    data_extra = {
        'suppression_reactive': defaultdict(int),
        'suppression_proactive': defaultdict(int),
        'causation_reactive': defaultdict(int),
        'causation_proactive': defaultdict(int)
    }
    data_missing = {
        'suppression_reactive': defaultdict(int),
        'suppression_proactive': defaultdict(int),
        'causation_reactive': defaultdict(int),
        'causation_proactive': defaultdict(int)
    }
    
    for block in diff_data.get('differing_blocks', []):
        timestamp = block['timestamp']
        block_type = block['block_type']  # 'reactive' or 'proactive'
        
        (causation_extra, causation_missing), (suppression_extra, suppression_missing) = count_differences(block)
        
        # Categorize by reactive/proactive
        if block_type == 'reactive':
            data_extra['suppression_reactive'][timestamp] += suppression_extra
            data_missing['suppression_reactive'][timestamp] += suppression_missing
            data_extra['causation_reactive'][timestamp] += causation_extra
            data_missing['causation_reactive'][timestamp] += causation_missing
        elif block_type == 'proactive':
            data_extra['suppression_proactive'][timestamp] += suppression_extra
            data_missing['suppression_proactive'][timestamp] += suppression_missing
            data_extra['causation_proactive'][timestamp] += causation_extra
            data_missing['causation_proactive'][timestamp] += causation_missing
    
    return data_extra, data_missing

def plot_diff_statistics(diff_dir):
    """Plot difference statistics for all partitions."""
    diff_dir = Path(diff_dir)
    
    # Find all diff files - look for any partition diff files (both formats)
    partition_files = sorted(diff_dir.glob('diff_*.json'))  # Match diff_1106.json, diff_1789.json, etc.
    combined_file = diff_dir / 'combined_partitions_diff.json'
    
    # Dictionary to store all partition data (separate extra and missing)
    all_data_extra = {}
    all_data_missing = {}
    
    # Load partition data
    for filepath in partition_files:
        # Extract partition ID from filename (e.g., "1106" from "diff_1106.json")
        stem = filepath.stem  # e.g., "diff_1106"
        if stem.startswith('diff_'):
            partition_id = stem.replace('diff_', '')  # e.g., "1106"
            partition_name = f'P{partition_id}'
        else:
            # Fallback for other naming patterns (e.g., "minitwit_gdpr_4_partition_1106_diff")
            stem = stem.replace('_diff', '')
            if 'partition_' in stem:
                partition_id = stem.split('partition_')[-1]
                partition_name = f'P{partition_id}'
            else:
                partition_name = stem
        
        diff_data = load_diff_file(filepath)
        data_extra, data_missing = extract_partition_data(diff_data)
        all_data_extra[partition_name] = data_extra
        all_data_missing[partition_name] = data_missing
    
    # Load combined data
    if combined_file.exists():
        combined_data = load_diff_file(combined_file)
        data_extra, data_missing = extract_partition_data(combined_data)
        all_data_extra['Combined'] = data_extra
        all_data_missing['Combined'] = data_missing
    
    # Get all timestamps
    all_timestamps = set()
    for data_extra in all_data_extra.values():
        for category in data_extra.values():
            all_timestamps.update(category.keys())
    for data_missing in all_data_missing.values():
        for category in data_missing.values():
            all_timestamps.update(category.keys())
    timestamps = sorted(all_timestamps)
    
    # Create figure with 4 subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Partition Differences Over Time (Separate: +Extra / -Missing)', fontsize=16, fontweight='bold')
    
    categories = [
        ('suppression_reactive', 'Suppression - Reactive', axes[0, 0]),
        ('suppression_proactive', 'Suppression - Proactive', axes[0, 1]),
        ('causation_reactive', 'Causation - Reactive', axes[1, 0]),
        ('causation_proactive', 'Causation - Proactive', axes[1, 1])
    ]
    
    # Color map for partitions
    partition_names = sorted([name for name in all_data_extra.keys() if name != 'Combined'])
    combined_name = 'Combined' if 'Combined' in all_data_extra else None
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(partition_names)))
    color_map = dict(zip(partition_names, colors))
    if combined_name:
        color_map[combined_name] = plt.cm.Set1(0)  # Different color for combined
    
    for cat_key, cat_title, ax in categories:
        # Skip if no data
        if not timestamps:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(cat_title, fontsize=14, fontweight='bold')
            continue
        
        # Prepare data for grouped bar chart (each partition gets its own bar group)
        x_positions = np.arange(len(timestamps))
        num_partitions = len(partition_names)
        
        # Calculate bar width and positions for grouped bars
        if combined_name:
            total_bars = num_partitions + 1  # partitions + combined
        else:
            total_bars = num_partitions
        
        bar_width = 0.8 / total_bars if total_bars > 0 else 0.8
        
        # Draw bars for each partition (separate bars for extra and missing)
        for idx, partition_name in enumerate(partition_names):
            data_extra = all_data_extra[partition_name]
            data_missing = all_data_missing[partition_name]
            
            values_extra = [data_extra[cat_key].get(t, 0) for t in timestamps]
            values_missing = [data_missing[cat_key].get(t, 0) for t in timestamps]
            
            # Calculate offset for this partition
            offset = (idx - num_partitions/2 + 0.5) * bar_width
            
            # Draw extra bars (positive, going up)
            bars_extra = ax.bar(x_positions + offset, values_extra, bar_width,
                               label=partition_name,
                               color=color_map[partition_name],
                               alpha=0.85,
                               edgecolor='black',
                               linewidth=0.5)
            
            # Draw missing bars (negative, going down) - no label to avoid duplicate
            bars_missing = ax.bar(x_positions + offset, values_missing, bar_width,
                                 color=np.array(color_map[partition_name]) * 0.6,  # Darker shade
                                 alpha=0.85,
                                 edgecolor='black',
                                 linewidth=0.5)
            
            # Add value labels on non-zero bars
            for i, (val_extra, val_missing) in enumerate(zip(values_extra, values_missing)):
                if val_extra > 0:
                    y_pos = val_extra + 0.3
                    ax.text(x_positions[i] + offset, y_pos, f'+{int(val_extra)}',
                           ha='center', va='bottom',
                           fontsize=7, fontweight='bold',
                           color=color_map[partition_name])
                if val_missing < 0:
                    y_pos = val_missing - 0.3
                    ax.text(x_positions[i] + offset, y_pos, str(int(val_missing)),
                           ha='center', va='top',
                           fontsize=7, fontweight='bold',
                           color=np.array(color_map[partition_name]) * 0.6)
        
        # Draw bars for combined (if exists)
        if combined_name:
            data_extra = all_data_extra[combined_name]
            data_missing = all_data_missing[combined_name]
            
            values_extra = [data_extra[cat_key].get(t, 0) for t in timestamps]
            values_missing = [data_missing[cat_key].get(t, 0) for t in timestamps]
            
            offset = (num_partitions - num_partitions/2 + 0.5) * bar_width
            
            # Draw extra bars (positive)
            bars_extra = ax.bar(x_positions + offset, values_extra, bar_width,
                               label=combined_name,
                               color=color_map[combined_name],
                               edgecolor='black',
                               linewidth=1.5,
                               alpha=0.85)
            
            # Draw missing bars (negative)
            bars_missing = ax.bar(x_positions + offset, values_missing, bar_width,
                                 color=np.array(color_map[combined_name]) * 0.6,
                                 edgecolor='black',
                                 linewidth=1.5,
                                 alpha=0.85)
            
            # Add value labels on non-zero bars
            for i, (val_extra, val_missing) in enumerate(zip(values_extra, values_missing)):
                if val_extra > 0:
                    y_pos = val_extra + 0.3
                    ax.text(x_positions[i] + offset, y_pos, f'+{int(val_extra)}',
                           ha='center', va='bottom',
                           fontsize=7, fontweight='bold',
                           color=color_map[combined_name])
                if val_missing < 0:
                    y_pos = val_missing - 0.3
                    ax.text(x_positions[i] + offset, y_pos, str(int(val_missing)),
                           ha='center', va='top',
                           fontsize=7, fontweight='bold',
                           color=np.array(color_map[combined_name]) * 0.6)
        
        # Add horizontal line at y=0
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.7)
        
        ax.set_xlabel('Timestamp', fontsize=12)
        ax.set_ylabel('Differences\n(+Extra / -Missing)', fontsize=12)
        ax.set_title(cat_title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Only show legend if there's data
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc='best', fontsize=9)
        
        # Set integer ticks on y-axis
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        # Set x-axis to show all timestamps
        ax.set_xticks(x_positions)
        ax.set_xticklabels(timestamps)
    
    plt.tight_layout()
    
    # Create plots directory at same level as diff directory
    plots_dir = diff_dir.parent.parent / 'plots'
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # Save figure
    output_path = plots_dir / 'partition_differences_plot.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")
    
    plt.close()  # Close instead of show to avoid GUI issues
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print("Legend: +N (extra in partition), -N (missing from partition), Net (sum)")
    
    for partition_name in sorted(all_data_extra.keys()):
        print(f"\n{partition_name}:")
        for cat_key, cat_title, _ in categories:
            values_extra = list(all_data_extra[partition_name][cat_key].values())
            values_missing = list(all_data_missing[partition_name][cat_key].values())
            
            if not values_extra and not values_missing:
                total_net = 0
                num_timestamps = 0
                total_positive = 0
                total_negative = 0
            else:
                total_positive = sum(values_extra)
                total_negative = sum(values_missing)
                total_net = total_positive + total_negative
                # Count unique timestamps with differences
                timestamps_with_diffs = set()
                for ts, val in all_data_extra[partition_name][cat_key].items():
                    if val != 0:
                        timestamps_with_diffs.add(ts)
                for ts, val in all_data_missing[partition_name][cat_key].items():
                    if val != 0:
                        timestamps_with_diffs.add(ts)
                num_timestamps = len(timestamps_with_diffs)
            
            sign = '+' if total_net > 0 else ''
            print(f"  {cat_title:30s}: Net={sign}{total_net:4d} (+{total_positive:3d} extra, {total_negative:4d} missing) across {num_timestamps} timestamps")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        diff_dir = sys.argv[1]
    else:
        diff_dir = 'tests/partition/results/minitwit_full_output/partition_outputs/diff'
    
    plot_diff_statistics(diff_dir)
