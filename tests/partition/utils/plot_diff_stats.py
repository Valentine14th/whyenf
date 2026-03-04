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
    """Count the number of differences in a diff block."""
    diffs = diff_block.get('differences', {})
    
    # Count causation differences
    causes_in_ref = len(diffs.get('causes', {}).get('only_in_reference', []))
    causes_in_part = len(diffs.get('causes', {}).get('only_in_partition', []))
    total_causation_diff = causes_in_ref + causes_in_part
    
    # Count suppression differences
    supp_in_ref = len(diffs.get('suppressions', {}).get('only_in_reference', []))
    supp_in_part = len(diffs.get('suppressions', {}).get('only_in_partition', []))
    total_suppression_diff = supp_in_ref + supp_in_part
    
    return total_causation_diff, total_suppression_diff

def extract_partition_data(diff_data):
    """Extract time-series data for a partition."""
    data = {
        'suppression_reactive': defaultdict(int),
        'suppression_proactive': defaultdict(int),
        'causation_reactive': defaultdict(int),
        'causation_proactive': defaultdict(int)
    }
    
    for block in diff_data.get('differing_blocks', []):
        timestamp = block['timestamp']
        block_type = block['block_type']  # 'reactive' or 'proactive'
        
        causation_diff, suppression_diff = count_differences(block)
        
        # Categorize by reactive/proactive
        if block_type == 'reactive':
            data['suppression_reactive'][timestamp] += suppression_diff
            data['causation_reactive'][timestamp] += causation_diff
        elif block_type == 'proactive':
            data['suppression_proactive'][timestamp] += suppression_diff
            data['causation_proactive'][timestamp] += causation_diff
    
    return data

def plot_diff_statistics(diff_dir):
    """Plot difference statistics for all partitions."""
    diff_dir = Path(diff_dir)
    
    # Find all diff files - look for any partition diff files
    partition_files = sorted(diff_dir.glob('*partition_*_diff.json'))
    combined_file = diff_dir / 'combined_partitions_diff.json'
    
    # Dictionary to store all partition data
    all_data = {}
    
    # Load partition data
    for filepath in partition_files:
        # Extract partition ID from filename (e.g., "1106" from "minitwit_gdpr_4_partition_1106_diff.json")
        stem = filepath.stem.replace('_diff', '')
        if 'partition_' in stem:
            partition_id = stem.split('partition_')[-1]
            partition_name = f'P{partition_id}'
        else:
            partition_name = stem
        
        diff_data = load_diff_file(filepath)
        all_data[partition_name] = extract_partition_data(diff_data)
    
    # Load combined data
    if combined_file.exists():
        combined_data = load_diff_file(combined_file)
        all_data['Combined'] = extract_partition_data(combined_data)
    
    # Get all timestamps
    all_timestamps = set()
    for data in all_data.values():
        for category in data.values():
            all_timestamps.update(category.keys())
    timestamps = sorted(all_timestamps)
    
    # Create figure with 4 subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Partition Differences Over Time', fontsize=16, fontweight='bold')
    
    categories = [
        ('suppression_reactive', 'Suppression - Reactive', axes[0, 0]),
        ('suppression_proactive', 'Suppression - Proactive', axes[0, 1]),
        ('causation_reactive', 'Causation - Reactive', axes[1, 0]),
        ('causation_proactive', 'Causation - Proactive', axes[1, 1])
    ]
    
    # Color map for partitions
    partition_names = sorted([name for name in all_data.keys() if name != 'Combined'])
    combined_name = 'Combined' if 'Combined' in all_data else None
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(partition_names)))
    color_map = dict(zip(partition_names, colors))
    if combined_name:
        color_map[combined_name] = plt.cm.Set1(0)  # Different color for combined
    
    for cat_key, cat_title, ax in categories:
        # Prepare data for stacked bar chart (individual partitions)
        bar_data = {}
        for partition_name in partition_names:
            data = all_data[partition_name]
            bar_data[partition_name] = [data[cat_key].get(t, 0) for t in timestamps]
        
        # Prepare data for combined (separate bars)
        combined_data = None
        if combined_name:
            combined_data = [all_data[combined_name][cat_key].get(t, 0) for t in timestamps]
        
        # Create grouped bars with offset
        bar_width = 0.35
        x_positions = np.arange(len(timestamps))
        
        # Draw stacked bars for individual partitions
        bottom = np.zeros(len(timestamps))
        for partition_name in partition_names:
            values = bar_data[partition_name]
            
            bars = ax.bar(x_positions - bar_width/2, values, bar_width, 
                         bottom=bottom,
                         label=partition_name,
                         color=color_map[partition_name],
                         alpha=0.85)
            
            # Add value labels on non-zero bars
            for i, val in enumerate(values):
                if val > 0:
                    # Position label in middle of this bar segment
                    y_pos = bottom[i] + val / 2
                    ax.text(x_positions[i] - bar_width/2, y_pos, str(val),
                           ha='center', va='center',
                           fontsize=8, fontweight='bold',
                           color='white' if val > 0.5 else 'black')
            
            bottom += np.array(values)
        
        # Draw separate bars for combined
        if combined_name and combined_data:
            bars = ax.bar(x_positions + bar_width/2, combined_data, bar_width,
                         label=combined_name,
                         color=color_map[combined_name],
                         edgecolor='black',
                         linewidth=1.5,
                         alpha=0.85)
            
            # Add value labels on non-zero bars
            for i, val in enumerate(combined_data):
                if val > 0:
                    ax.text(x_positions[i] + bar_width/2, val/2, str(val),
                           ha='center', va='center',
                           fontsize=8, fontweight='bold',
                           color='white' if val > 0.5 else 'black')
        
        ax.set_xlabel('Timestamp', fontsize=12)
        ax.set_ylabel('Number of Differences', fontsize=12)
        ax.set_title(cat_title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set y-axis to always start at 0
        ax.set_ylim(bottom=0)
        
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
    
    for partition_name, data in sorted(all_data.items()):
        print(f"\n{partition_name}:")
        for cat_key, cat_title, _ in categories:
            total_diffs = sum(data[cat_key].values())
            num_timestamps = len([v for v in data[cat_key].values() if v > 0])
            print(f"  {cat_title:30s}: {total_diffs:4d} total differences across {num_timestamps} timestamps")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        diff_dir = sys.argv[1]
    else:
        diff_dir = 'tests/partition/results/minitwit_full_output/partition_outputs/diff'
    
    plot_diff_statistics(diff_dir)
