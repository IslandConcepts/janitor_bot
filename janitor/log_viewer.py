#!/usr/bin/env python3

"""
Log viewer and analyzer for janitor bot logs
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

def parse_json_log(log_path: Path, start_time: Optional[datetime] = None, 
                   end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Parse JSON log file and filter by time range"""
    logs = []
    
    with open(log_path, 'r') as f:
        for line in f:
            try:
                log = json.loads(line.strip())
                log_time = datetime.fromisoformat(log['timestamp'])
                
                # Apply time filters
                if start_time and log_time < start_time:
                    continue
                if end_time and log_time > end_time:
                    continue
                    
                logs.append(log)
            except (json.JSONDecodeError, KeyError):
                continue
    
    return logs

def analyze_transactions(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze transaction logs"""
    transactions = []
    for log in logs:
        if log.get('tx_hash'):
            transactions.append({
                'timestamp': log['timestamp'],
                'target': log.get('target', 'Unknown'),
                'chain': log.get('chain', 'Unknown'),
                'tx_hash': log['tx_hash'],
                'profit_usd': log.get('profit_usd', 0),
                'gas_used': log.get('gas_used', 0)
            })
    
    if not transactions:
        return {'count': 0, 'total_profit': 0}
    
    total_profit = sum(tx['profit_usd'] for tx in transactions)
    avg_profit = total_profit / len(transactions) if transactions else 0
    
    return {
        'count': len(transactions),
        'total_profit': total_profit,
        'avg_profit': avg_profit,
        'transactions': transactions[-10:]  # Last 10
    }

def analyze_errors(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze error logs"""
    errors = defaultdict(list)
    
    for log in logs:
        if log['level'] in ['ERROR', 'CRITICAL']:
            error_type = log.get('error_type', 'general')
            errors[error_type].append({
                'timestamp': log['timestamp'],
                'message': log['message'],
                'target': log.get('target'),
                'chain': log.get('chain')
            })
    
    error_summary = {}
    for error_type, error_list in errors.items():
        error_summary[error_type] = {
            'count': len(error_list),
            'recent': error_list[-5:]  # Last 5 errors
        }
    
    return error_summary

def analyze_performance(log_path: Path) -> Dict[str, Any]:
    """Analyze performance logs"""
    perf_logs = parse_json_log(log_path.parent / 'performance.log')
    
    operations = defaultdict(lambda: {'count': 0, 'total_duration': 0, 'success': 0})
    
    for log in perf_logs:
        op = log.get('operation', 'unknown')
        duration = log.get('duration_ms', 0)
        success = log.get('success', False)
        
        operations[op]['count'] += 1
        operations[op]['total_duration'] += duration
        if success:
            operations[op]['success'] += 1
    
    # Calculate averages and success rates
    perf_summary = {}
    for op, stats in operations.items():
        perf_summary[op] = {
            'avg_duration_ms': stats['total_duration'] / stats['count'] if stats['count'] else 0,
            'success_rate': (stats['success'] / stats['count'] * 100) if stats['count'] else 0,
            'total_calls': stats['count']
        }
    
    return perf_summary

def print_summary(logs: List[Dict[str, Any]], args):
    """Print log summary"""
    print("\n" + "="*60)
    print(f"LOG ANALYSIS SUMMARY")
    print("="*60)
    
    # Time range
    if logs:
        first_log = datetime.fromisoformat(logs[0]['timestamp'])
        last_log = datetime.fromisoformat(logs[-1]['timestamp'])
        print(f"\nTime Range: {first_log} to {last_log}")
        print(f"Total Logs: {len(logs)}")
    
    # Log levels
    level_counts = defaultdict(int)
    for log in logs:
        level_counts[log['level']] += 1
    
    print("\nLog Levels:")
    for level, count in sorted(level_counts.items()):
        print(f"  {level:8} : {count:6}")
    
    # Transaction analysis
    if args.transactions:
        tx_analysis = analyze_transactions(logs)
        print("\n" + "-"*40)
        print("TRANSACTIONS")
        print("-"*40)
        print(f"Total: {tx_analysis['count']}")
        print(f"Total Profit: ${tx_analysis['total_profit']:.2f}")
        print(f"Avg Profit: ${tx_analysis['avg_profit']:.4f}")
        
        if tx_analysis['transactions']:
            print("\nRecent Transactions:")
            for tx in tx_analysis['transactions'][-5:]:
                print(f"  {tx['timestamp']}: {tx['target'][:15]} - ${tx['profit_usd']:.4f} ({tx['tx_hash'][:10]}...)")
    
    # Error analysis
    if args.errors:
        error_analysis = analyze_errors(logs)
        if error_analysis:
            print("\n" + "-"*40)
            print("ERRORS")
            print("-"*40)
            for error_type, data in error_analysis.items():
                print(f"\n{error_type}: {data['count']} occurrences")
                for err in data['recent'][-3:]:
                    print(f"  {err['timestamp']}: {err['message'][:60]}...")
    
    # Performance analysis
    if args.performance:
        perf_analysis = analyze_performance(Path(args.log_file))
        if perf_analysis:
            print("\n" + "-"*40)
            print("PERFORMANCE")
            print("-"*40)
            for op, stats in sorted(perf_analysis.items(), key=lambda x: x[1]['total_calls'], reverse=True)[:10]:
                print(f"{op:20} : {stats['avg_duration_ms']:7.2f}ms avg | "
                      f"{stats['success_rate']:5.1f}% success | {stats['total_calls']} calls")

def tail_logs(log_path: Path, follow: bool = False):
    """Tail log file (similar to tail -f)"""
    with open(log_path, 'r') as f:
        if not follow:
            # Just print last 20 lines
            lines = f.readlines()
            for line in lines[-20:]:
                try:
                    log = json.loads(line.strip())
                    print(f"[{log['timestamp']}] {log['level']:8} {log['message']}")
                except:
                    print(line.strip())
        else:
            # Follow mode
            import time
            f.seek(0, 2)  # Go to end of file
            while True:
                line = f.readline()
                if line:
                    try:
                        log = json.loads(line.strip())
                        print(f"[{log['timestamp']}] {log['level']:8} {log['message']}")
                    except:
                        print(line.strip())
                else:
                    time.sleep(0.1)

def main():
    parser = argparse.ArgumentParser(description='Janitor Bot Log Viewer')
    parser.add_argument('--log-file', default='data/logs/janitor.json', 
                       help='Path to log file')
    parser.add_argument('--start', help='Start time (ISO format)')
    parser.add_argument('--end', help='End time (ISO format)')
    parser.add_argument('--hours', type=int, help='Last N hours')
    parser.add_argument('--level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Filter by log level')
    parser.add_argument('--target', help='Filter by target name')
    parser.add_argument('--chain', help='Filter by chain')
    parser.add_argument('--transactions', action='store_true', 
                       help='Analyze transactions')
    parser.add_argument('--errors', action='store_true', 
                       help='Analyze errors')
    parser.add_argument('--performance', action='store_true', 
                       help='Analyze performance')
    parser.add_argument('--tail', action='store_true', 
                       help='Tail mode (show last lines)')
    parser.add_argument('--follow', action='store_true', 
                       help='Follow mode (like tail -f)')
    
    args = parser.parse_args()
    
    log_path = Path(args.log_file)
    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        sys.exit(1)
    
    # Handle tail mode
    if args.tail or args.follow:
        tail_logs(log_path, args.follow)
        return
    
    # Parse time range
    start_time = None
    end_time = None
    
    if args.hours:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=args.hours)
    elif args.start:
        start_time = datetime.fromisoformat(args.start)
    if args.end:
        end_time = datetime.fromisoformat(args.end)
    
    # Parse logs
    logs = parse_json_log(log_path, start_time, end_time)
    
    # Apply filters
    if args.level:
        logs = [log for log in logs if log['level'] == args.level]
    if args.target:
        logs = [log for log in logs if log.get('target') == args.target]
    if args.chain:
        logs = [log for log in logs if log.get('chain') == args.chain]
    
    # Print summary
    print_summary(logs, args)

if __name__ == "__main__":
    main()