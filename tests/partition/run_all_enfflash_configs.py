#!/usr/bin/env python3
"""
Script to run all enfflash config.yaml workflows sequentially.
Usage: python3 run_all_enfflash_configs.py [--pattern PATTERN] [--parallel]
"""

import os
import sys
import glob
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
import time

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color
    BOLD = '\033[1m'

def print_colored(text, color=Colors.NC):
    """Print text with color."""
    print(f"{color}{text}{Colors.NC}")

def check_python_dependencies():
    """Validate dependencies before starting a long batch run."""
    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError as exc:
        if exc.name != 'yaml':
            raise
        print_colored("Missing Python dependency: PyYAML", Colors.RED)
        print_colored(f"Interpreter: {sys.executable}", Colors.YELLOW)
        print_colored(f"Install it with: {sys.executable} -m pip install PyYAML", Colors.YELLOW)
        return False
    return True

def run_workflow(config_file, output_name, script_dir, log_file):
    """Run a single workflow and return success status."""
    workflow_script = os.path.join(script_dir, "run_partition_workflow.py")
    
    print_colored(f"\n{'='*60}", Colors.CYAN)
    print_colored(f"Running: {os.path.basename(config_file)}", Colors.BOLD)
    print_colored(f"Output: {output_name}", Colors.CYAN)
    print_colored(f"{'='*60}\n", Colors.CYAN)
    
    start_time = time.time()
    
    # Log to file
    with open(log_file, 'a') as log:
        log.write(f"\n{'='*60}\n")
        log.write(f"Config: {os.path.basename(config_file)}\n")
        log.write(f"Output: {output_name}\n")
        log.write(f"Start: {datetime.now()}\n")
        log.write(f"{'='*60}\n\n")
    
    # Run the workflow
    try:
        result = subprocess.run(
            [sys.executable, workflow_script, config_file, output_name],
            capture_output=False,  # Show output in real-time
            text=True,
            timeout=7200  # 2 hour timeout per workflow
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print_colored(f"\n✓ Success (took {elapsed:.1f}s)", Colors.GREEN)
            with open(log_file, 'a') as log:
                log.write(f"\n✓ Success (took {elapsed:.1f}s)\n")
                log.write(f"End: {datetime.now()}\n\n")
            return True
        else:
            print_colored(f"\n✗ Failed with return code {result.returncode} (took {elapsed:.1f}s)", Colors.RED)
            with open(log_file, 'a') as log:
                log.write(f"\n✗ Failed with return code {result.returncode} (took {elapsed:.1f}s)\n")
                log.write(f"End: {datetime.now()}\n\n")
            return False
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print_colored(f"\n✗ Timeout after {elapsed:.1f}s", Colors.RED)
        with open(log_file, 'a') as log:
            log.write(f"\n✗ Timeout after {elapsed:.1f}s\n")
            log.write(f"End: {datetime.now()}\n\n")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print_colored(f"\n✗ Error: {e} (after {elapsed:.1f}s)", Colors.RED)
        with open(log_file, 'a') as log:
            log.write(f"\n✗ Error: {e} (after {elapsed:.1f}s)\n")
            log.write(f"End: {datetime.now()}\n\n")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Run all enfflash config workflows',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all configs matching pattern
  python3 run_all_enfflash_configs.py --pattern "minitwit_enfflash*.yaml"
  
  # Run specific configs in order
  python3 run_all_enfflash_configs.py config1.yaml config2.yaml config3.yaml
  
  # Run configs listed in a file
  python3 run_all_enfflash_configs.py --config-list my_configs.txt
        """
    )
    parser.add_argument(
        'configs',
        nargs='*',
        help='Specific config files to run (in order). Can be basenames or full paths.'
    )
    parser.add_argument(
        '--config-list',
        help='Path to text file containing list of config files (one per line)'
    )
    parser.add_argument(
        '--pattern',
        default='minitwit_enfflash*.yaml',
        help='Glob pattern for config files (default: minitwit_enfflash*.yaml). Only used if no configs specified.'
    )
    parser.add_argument(
        '--configs-dir',
        default=None,
        help='Directory containing config files (default: ./configs)'
    )
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue running even if a config fails'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show which configs would be run without executing'
    )
    
    args = parser.parse_args()

    if not check_python_dependencies():
        return 1
    
    # Determine directories
    script_dir = Path(__file__).parent.resolve()
    configs_dir = Path(args.configs_dir) if args.configs_dir else script_dir / "configs"
    results_dir = script_dir / "results"
    
    # Create results directory
    results_dir.mkdir(exist_ok=True)
    
    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = results_dir / f"batch_run_{timestamp}.log"
    
    # Determine which config files to run
    config_files = []
    
    if args.config_list:
        # Read from config list file
        list_file = Path(args.config_list)
        if not list_file.exists():
            print_colored(f"Config list file not found: {args.config_list}", Colors.RED)
            return 1
        
        with open(list_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Support both basename and full path
                    if os.path.isabs(line):
                        config_path = Path(line)
                    else:
                        config_path = configs_dir / line
                    
                    if config_path.exists():
                        config_files.append(str(config_path))
                    else:
                        print_colored(f"Warning: Config file not found: {config_path}", Colors.YELLOW)
        
        print_colored(f"Loaded {len(config_files)} configs from {args.config_list}", Colors.CYAN)
    
    elif args.configs:
        # Use explicitly specified configs
        for config in args.configs:
            # Support both basename and full path
            if os.path.isabs(config):
                config_path = Path(config)
            else:
                # Try as relative path, then in configs_dir
                config_path = Path(config)
                if not config_path.exists():
                    config_path = configs_dir / config
            
            if config_path.exists():
                config_files.append(str(config_path))
            else:
                print_colored(f"Warning: Config file not found: {config_path}", Colors.YELLOW)
        
        print_colored(f"Using {len(config_files)} explicitly specified configs", Colors.CYAN)
    
    else:
        # Fall back to pattern matching
        config_pattern = str(configs_dir / args.pattern)
        config_files = sorted(glob.glob(config_pattern))
        print_colored(f"Using pattern: {args.pattern}", Colors.CYAN)
    
    if not config_files:
        print_colored(f"No config files to process", Colors.RED)
        return 1
    
    # Print header
    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("Running All Enfflash Workflow Configs", Colors.BOLD + Colors.BLUE)
    print_colored("="*60, Colors.BLUE)
    print_colored(f"Start time: {datetime.now()}", Colors.BLUE)
    
    if args.config_list:
        print_colored(f"Config list file: {args.config_list}", Colors.BLUE)
    elif args.configs:
        print_colored(f"Mode: Explicit config list", Colors.BLUE)
    else:
        print_colored(f"Config pattern: {args.pattern}", Colors.BLUE)
    
    print_colored(f"Configs directory: {configs_dir}", Colors.BLUE)
    print_colored(f"Total configs: {len(config_files)}", Colors.BLUE)
    print_colored(f"Batch log: {log_file}", Colors.BLUE)
    print_colored("="*60 + "\n", Colors.BLUE)
    
    # Initialize batch log
    with open(log_file, 'w') as log:
        log.write(f"Batch run started at {datetime.now()}\n")
        if args.config_list:
            log.write(f"Config list file: {args.config_list}\n")
        elif args.configs:
            log.write(f"Mode: Explicit config list\n")
        else:
            log.write(f"Config pattern: {args.pattern}\n")
        log.write(f"Total configs: {len(config_files)}\n")
        log.write("="*60 + "\n")
    
    # List configs
    if args.dry_run:
        print_colored("Dry run - would process:", Colors.YELLOW)
        for i, config_file in enumerate(config_files, 1):
            print(f"  [{i}] {os.path.basename(config_file)}")
        return 0
    
    # Run each workflow
    results = []
    start_time = time.time()
    
    for i, config_file in enumerate(config_files, 1):
        config_basename = Path(config_file).stem
        output_name = f"enfflash_{config_basename}_{timestamp}"
        
        print_colored(f"\n[{i}/{len(config_files)}] Processing: {config_basename}", Colors.YELLOW)
        
        success = run_workflow(config_file, output_name, script_dir, log_file)
        results.append({
            'config': config_basename,
            'success': success,
            'output': output_name
        })
        
        if not success and not args.continue_on_error:
            print_colored(f"\nStopping due to failure. Use --continue-on-error to continue.", Colors.RED)
            break
    
    total_time = time.time() - start_time
    
    # Print summary
    success_count = sum(1 for r in results if r['success'])
    failed_count = len(results) - success_count
    
    print_colored(f"\n{'='*60}", Colors.BLUE)
    print_colored("Batch Run Summary", Colors.BOLD + Colors.BLUE)
    print_colored("="*60, Colors.BLUE)
    print_colored(f"End time: {datetime.now()}", Colors.BLUE)
    print_colored(f"Total time: {total_time/60:.1f} minutes", Colors.BLUE)
    print_colored(f"Total configs: {len(results)}", Colors.BLUE)
    print_colored(f"Successful: {success_count}", Colors.GREEN)
    if failed_count > 0:
        print_colored(f"Failed: {failed_count}", Colors.RED)
    else:
        print(f"Failed: {failed_count}")
    print_colored(f"Batch log: {log_file}", Colors.BLUE)
    print_colored("="*60 + "\n", Colors.BLUE)
    
    # Print individual results
    if failed_count > 0:
        print_colored("Failed configs:", Colors.RED)
        for r in results:
            if not r['success']:
                print(f"  ✗ {r['config']}")
    
    # Write summary to log
    with open(log_file, 'a') as log:
        log.write(f"\n{'='*60}\n")
        log.write(f"Batch run completed at {datetime.now()}\n")
        log.write(f"Total time: {total_time/60:.1f} minutes\n")
        log.write(f"Total: {len(results)} | Success: {success_count} | Failed: {failed_count}\n")
        log.write("="*60 + "\n")
    
    return 1 if failed_count > 0 else 0

if __name__ == '__main__':
    sys.exit(main())
