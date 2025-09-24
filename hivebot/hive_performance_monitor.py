#!/usr/bin/env python3

"""
Hive Performance Monitor - Independent System Resource Monitoring
Measures and compares resource usage between Hivebot (1:N) and original Hummingbot (1:1).
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import psutil


class ProcessMonitor:
    """Monitor system resources for a specific process."""

    def __init__(self, process_name: str, pid: Optional[int] = None, aggregate_instances: bool = False):
        self.process_name = process_name
        self.target_pid = pid
        self.aggregate_instances = aggregate_instances  # New: aggregate all instances of this process
        self.process = None
        self.processes = []  # New: for multi-instance monitoring
        self.start_time = None
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 measurements

    def find_process(self) -> Optional[psutil.Process]:
        """Find the target process by name or PID."""
        try:
            if self.target_pid:
                return psutil.Process(self.target_pid)

            # Search by process name
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if (self.process_name.lower() in proc.info['name'].lower() or
                        any(self.process_name.lower() in arg.lower()
                            for arg in (proc.info['cmdline'] or []))):
                        return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None
        except Exception as e:
            logging.error(f"Error finding process {self.process_name}: {e}")
            return None

    def find_all_processes(self) -> List[psutil.Process]:
        """Find ALL processes matching the target name (for aggregation)."""
        matching_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if (self.process_name.lower() in proc.info['name'].lower() or
                        any(self.process_name.lower() in arg.lower()
                            for arg in (proc.info['cmdline'] or []))):
                        matching_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logging.error(f"Error finding processes {self.process_name}: {e}")

        return matching_processes

    def get_metrics(self) -> Optional[Dict]:
        """Get current resource metrics for the process(es)."""
        if self.aggregate_instances:
            return self._get_aggregated_metrics()
        else:
            return self._get_single_process_metrics()

    def _get_single_process_metrics(self) -> Optional[Dict]:
        """Get metrics for a single process (original behavior)."""
        if not self.process or not self.process.is_running():
            self.process = self.find_process()
            if not self.process:
                return None

        try:
            # Basic process info
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()

            # Get all child processes for total resource calculation
            children = self.process.children(recursive=True)
            total_memory_rss = memory_info.rss
            total_memory_vms = memory_info.vms
            total_cpu = cpu_percent

            # Include children's resource usage
            for child in children:
                try:
                    child_memory = child.memory_info()
                    total_memory_rss += child_memory.rss
                    total_memory_vms += child_memory.vms
                    total_cpu += child.cpu_percent()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Network I/O (system-wide, as process-specific may not be available)
            try:
                net_io = psutil.net_io_counters()
                network_bytes_sent = net_io.bytes_sent if net_io else 0
                network_bytes_recv = net_io.bytes_recv if net_io else 0
            except:
                network_bytes_sent = network_bytes_recv = 0

            # File handles
            try:
                num_fds = self.process.num_fds() if hasattr(self.process, 'num_fds') else 0
            except:
                num_fds = 0

            # Thread count
            try:
                num_threads = self.process.num_threads()
            except:
                num_threads = 0

            metrics = {
                'timestamp': datetime.now().isoformat(),
                'pid': self.process.pid,
                'name': self.process.name(),
                'cpu_percent': round(total_cpu, 2),
                'memory_rss_mb': round(total_memory_rss / (1024 * 1024), 2),
                'memory_vms_mb': round(total_memory_vms / (1024 * 1024), 2),
                'memory_percent': round(self.process.memory_percent(), 2),
                'num_threads': num_threads,
                'num_fds': num_fds,
                'network_bytes_sent': network_bytes_sent,
                'network_bytes_recv': network_bytes_recv,
                'num_children': len(children),
                'process_count': 1  # Single process
            }

            return metrics

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logging.warning(f"Process {self.process_name} no longer accessible: {e}")
            self.process = None
            return None
        except Exception as e:
            logging.error(f"Error getting metrics for {self.process_name}: {e}")
            return None

    def _get_aggregated_metrics(self) -> Optional[Dict]:
        """Get aggregated metrics for ALL instances of this process type."""
        # Refresh process list
        self.processes = self.find_all_processes()

        if not self.processes:
            return None

        # Aggregate metrics across all instances
        total_cpu = 0.0
        total_memory_rss = 0
        total_memory_vms = 0
        total_threads = 0
        total_fds = 0
        total_children = 0
        active_processes = 0
        pids = []

        for proc in self.processes:
            try:
                # Basic process metrics
                memory_info = proc.memory_info()
                cpu_percent = proc.cpu_percent()

                # Include children
                children = proc.children(recursive=True)
                proc_memory_rss = memory_info.rss
                proc_memory_vms = memory_info.vms
                proc_cpu = cpu_percent

                for child in children:
                    try:
                        child_memory = child.memory_info()
                        proc_memory_rss += child_memory.rss
                        proc_memory_vms += child_memory.vms
                        proc_cpu += child.cpu_percent()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Aggregate totals
                total_cpu += proc_cpu
                total_memory_rss += proc_memory_rss
                total_memory_vms += proc_memory_vms

                try:
                    total_threads += proc.num_threads()
                except:
                    pass

                try:
                    total_fds += proc.num_fds() if hasattr(proc, 'num_fds') else 0
                except:
                    pass

                total_children += len(children)
                active_processes += 1
                pids.append(proc.pid)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                logging.warning(f"Error getting metrics for process {proc.pid}: {e}")
                continue

        if active_processes == 0:
            return None

        # Network I/O (system-wide)
        try:
            net_io = psutil.net_io_counters()
            network_bytes_sent = net_io.bytes_sent if net_io else 0
            network_bytes_recv = net_io.bytes_recv if net_io else 0
        except:
            network_bytes_sent = network_bytes_recv = 0

        # Calculate memory percentage (approximate)
        memory_percent = (total_memory_rss / (psutil.virtual_memory().total)) * 100

        aggregated_metrics = {
            'timestamp': datetime.now().isoformat(),
            'pid': f"[{','.join(map(str, pids[:5]))}{'...' if len(pids) > 5 else ''}]",  # Show first 5 PIDs
            'name': f"{self.process_name} (aggregated)",
            'cpu_percent': round(total_cpu, 2),
            'memory_rss_mb': round(total_memory_rss / (1024 * 1024), 2),
            'memory_vms_mb': round(total_memory_vms / (1024 * 1024), 2),
            'memory_percent': round(memory_percent, 2),
            'num_threads': total_threads,
            'num_fds': total_fds,
            'network_bytes_sent': network_bytes_sent,
            'network_bytes_recv': network_bytes_recv,
            'num_children': total_children,
            'process_count': active_processes  # Number of instances found
        }

        return aggregated_metrics

    def record_metrics(self):
        """Record current metrics to history."""
        metrics = self.get_metrics()
        if metrics:
            self.metrics_history.append(metrics)
            if not self.start_time:
                self.start_time = datetime.now()
        return metrics


class PerformanceComparator:
    """Compare performance between different systems/processes."""

    def __init__(self):
        self.monitors: Dict[str, ProcessMonitor] = {}
        self.system_baseline = None
        self.running = False

    def add_monitor(self, name: str, process_name: str, pid: Optional[int] = None, aggregate_instances: bool = False):
        """Add a process to monitor."""
        self.monitors[name] = ProcessMonitor(process_name, pid, aggregate_instances)
        if aggregate_instances:
            logging.info(f"Added aggregated monitor for '{name}' tracking ALL instances of '{process_name}'")
        else:
            logging.info(f"Added monitor for '{name}' tracking process '{process_name}'")

    def get_system_baseline(self) -> Dict:
        """Get system-wide resource baseline."""
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_count': cpu_count,
            'cpu_percent': psutil.cpu_percent(),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'memory_available_gb': round(memory.available / (1024**3), 2),
            'memory_used_percent': memory.percent,
            'disk_total_gb': round(disk.total / (1024**3), 2),
            'disk_free_gb': round(disk.free / (1024**3), 2),
            'disk_used_percent': round((disk.used / disk.total) * 100, 1)
        }

    def start_monitoring(self, duration_minutes: Optional[int] = None, interval_seconds: int = 5):
        """Start monitoring all processes."""
        self.running = True
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60) if duration_minutes else None

        # Record system baseline
        self.system_baseline = self.get_system_baseline()
        logging.info("📊 Performance monitoring started")
        logging.info(f"System: {self.system_baseline['cpu_count']} CPUs, "
                     f"{self.system_baseline['memory_total_gb']}GB RAM")

        try:
            while self.running:
                current_time = time.time()

                # Check if we should stop
                if end_time and current_time >= end_time:
                    break

                # Record metrics for all monitors
                active_monitors = []
                for name, monitor in self.monitors.items():
                    metrics = monitor.record_metrics()
                    if metrics:
                        if monitor.aggregate_instances:
                            active_monitors.append(f"{name}({metrics['process_count']} instances)")
                        else:
                            active_monitors.append(f"{name}({metrics['pid']})")

                if active_monitors:
                    logging.info(f"📈 Monitoring: {', '.join(active_monitors)}")
                else:
                    logging.warning("⚠️ No active processes found to monitor")

                # Wait for next interval
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logging.info("📊 Monitoring interrupted by user")
        finally:
            self.running = False
            logging.info("📊 Performance monitoring stopped")

    def generate_report(self, output_file: Optional[str] = None) -> Dict:
        """Generate performance comparison report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'system_baseline': self.system_baseline,
            'processes': {},
            'summary': {},
            'comparison': {}
        }

        # Process individual monitor data
        for name, monitor in self.monitors.items():
            if not monitor.metrics_history:
                continue

            metrics_list = list(monitor.metrics_history)
            if not metrics_list:
                continue

            # Calculate statistics
            cpu_values = [m['cpu_percent'] for m in metrics_list]
            memory_values = [m['memory_rss_mb'] for m in metrics_list]
            thread_values = [m['num_threads'] for m in metrics_list]

            process_stats = {
                'process_name': monitor.process_name,
                'aggregated_instances': monitor.aggregate_instances,
                'monitoring_duration_minutes': round((datetime.now() - monitor.start_time).total_seconds() / 60, 2) if monitor.start_time else 0,
                'samples_collected': len(metrics_list),
                'avg_process_count': round(sum(m.get('process_count', 1) for m in metrics_list) / len(metrics_list), 2) if monitor.aggregate_instances else 1,
                'cpu': {
                    'avg_percent': round(sum(cpu_values) / len(cpu_values), 2),
                    'max_percent': round(max(cpu_values), 2),
                    'min_percent': round(min(cpu_values), 2)
                },
                'memory': {
                    'avg_mb': round(sum(memory_values) / len(memory_values), 2),
                    'max_mb': round(max(memory_values), 2),
                    'min_mb': round(min(memory_values), 2),
                    'avg_percent': round(sum(m['memory_percent'] for m in metrics_list) / len(metrics_list), 2)
                },
                'threads': {
                    'avg_count': round(sum(thread_values) / len(thread_values), 2),
                    'max_count': max(thread_values),
                    'min_count': min(thread_values)
                },
                'children_processes': {
                    'avg_count': round(sum(m['num_children'] for m in metrics_list) / len(metrics_list), 2),
                    'max_count': max(m['num_children'] for m in metrics_list)
                },
                'latest_metrics': metrics_list[-1] if metrics_list else None
            }

            report['processes'][name] = process_stats

        # Generate comparison if we have multiple processes
        if len(report['processes']) >= 2:
            process_names = list(report['processes'].keys())
            comparisons = {}

            for i in range(len(process_names)):
                for j in range(i + 1, len(process_names)):
                    name1, name2 = process_names[i], process_names[j]
                    proc1, proc2 = report['processes'][name1], report['processes'][name2]

                    comparison_key = f"{name1}_vs_{name2}"
                    comparisons[comparison_key] = {
                        'cpu_efficiency': {
                            f'{name1}_avg_cpu': proc1['cpu']['avg_percent'],
                            f'{name2}_avg_cpu': proc2['cpu']['avg_percent'],
                            'cpu_advantage': name1 if proc1['cpu']['avg_percent'] < proc2['cpu']['avg_percent'] else name2,
                            'cpu_savings_percent': abs(proc1['cpu']['avg_percent'] - proc2['cpu']['avg_percent'])
                        },
                        'memory_efficiency': {
                            f'{name1}_avg_memory_mb': proc1['memory']['avg_mb'],
                            f'{name2}_avg_memory_mb': proc2['memory']['avg_mb'],
                            'memory_advantage': name1 if proc1['memory']['avg_mb'] < proc2['memory']['avg_mb'] else name2,
                            'memory_savings_mb': abs(proc1['memory']['avg_mb'] - proc2['memory']['avg_mb'])
                        },
                        'process_efficiency': {
                            f'{name1}_avg_children': proc1['children_processes']['avg_count'],
                            f'{name2}_avg_children': proc2['children_processes']['avg_count'],
                            'process_advantage': name1 if proc1['children_processes']['avg_count'] < proc2['children_processes']['avg_count'] else name2
                        }
                    }

            report['comparison'] = comparisons

        # Generate summary
        if report['processes']:
            total_avg_cpu = sum(p['cpu']['avg_percent'] for p in report['processes'].values())
            total_avg_memory = sum(p['memory']['avg_mb'] for p in report['processes'].values())

            report['summary'] = {
                'total_processes_monitored': len(report['processes']),
                'total_avg_cpu_percent': round(total_avg_cpu, 2),
                'total_avg_memory_mb': round(total_avg_memory, 2),
                'monitoring_period_minutes': max(p.get('monitoring_duration_minutes', 0) for p in report['processes'].values())
            }

        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logging.info(f"📄 Report saved to: {output_file}")

        return report

    def print_live_summary(self):
        """Print a live summary of current metrics."""
        if not self.monitors:
            print("No processes being monitored")
            return

        print("\n" + "=" * 80)
        print(f"📊 LIVE PERFORMANCE MONITOR - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)

        for name, monitor in self.monitors.items():
            metrics = monitor.get_metrics()
            if metrics:
                print(f"🔸 {name.upper()}")
                if monitor.aggregate_instances:
                    print(f"   Instances: {metrics['process_count']} | CPU: {metrics['cpu_percent']}% | "
                          f"RAM: {metrics['memory_rss_mb']}MB ({metrics['memory_percent']}%) | "
                          f"Threads: {metrics['num_threads']} | Children: {metrics['num_children']}")
                else:
                    print(f"   PID: {metrics['pid']} | CPU: {metrics['cpu_percent']}% | "
                          f"RAM: {metrics['memory_rss_mb']}MB ({metrics['memory_percent']}%) | "
                          f"Threads: {metrics['num_threads']} | Children: {metrics['num_children']}")
            else:
                print(f"🔸 {name.upper()}: Process not found or not accessible")

        print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Hive Performance Monitor - Compare resource usage between systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fair comparison: Hivebot (1 process) vs Hummingbot (aggregate ALL instances)
  python hive_performance_monitor.py --hive "hive_dynamic_core" --hummingbot "hummingbot" --aggregate-hummingbot

  # Monitor specific PIDs
  python hive_performance_monitor.py --hive-pid 1234 --hummingbot-pid 5678

  # Long-term comparison with aggregation (recommended)
  python hive_performance_monitor.py --hive "hive" --hummingbot "hummingbot" --aggregate-hummingbot --duration 30 --interval 10

  # Live monitoring with aggregation
  python hive_performance_monitor.py --hive "hive" --hummingbot "hummingbot" --aggregate-hummingbot --live
        """
    )

    parser.add_argument("--hive", help="Hivebot process name to monitor")
    parser.add_argument("--hive-pid", type=int, help="Hivebot process PID to monitor")
    parser.add_argument("--hummingbot", help="Hummingbot process name to monitor")
    parser.add_argument("--hummingbot-pid", type=int, help="Hummingbot process PID to monitor")
    parser.add_argument("--aggregate-hummingbot", action="store_true", help="Aggregate ALL Hummingbot instances for fair comparison (recommended)")
    parser.add_argument("--duration", type=int, help="Monitoring duration in minutes")
    parser.add_argument("--interval", type=int, default=5, help="Monitoring interval in seconds (default: 5)")
    parser.add_argument("--output", help="Output file for performance report (JSON)")
    parser.add_argument("--report-only", action="store_true", help="Generate report only (no monitoring)")
    parser.add_argument("--live", action="store_true", help="Show live metrics every interval")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Create comparator
    comparator = PerformanceComparator()

    # Add monitors based on arguments
    if args.hive or args.hive_pid:
        comparator.add_monitor("HIVEBOT", args.hive or "hive", args.hive_pid)

    if args.hummingbot or args.hummingbot_pid:
        # Use aggregation for hummingbot if requested (recommended for fair comparison)
        aggregate = args.aggregate_hummingbot and not args.hummingbot_pid  # Can't aggregate if specific PID given
        comparator.add_monitor("HUMMINGBOT", args.hummingbot or "hummingbot", args.hummingbot_pid, aggregate)

    if not comparator.monitors and not args.report_only:
        print("❌ No processes specified to monitor. Use --hive, --hummingbot, or their PID variants.")
        return 1

    # Handle report-only mode
    if args.report_only:
        print("📊 Generating performance report from existing data...")
        report = comparator.generate_report(args.output)
        print(json.dumps(report, indent=2))
        return 0

    # Start monitoring
    try:
        if args.live:
            # Live monitoring mode
            while True:
                comparator.print_live_summary()
                time.sleep(args.interval)
        else:
            # Standard monitoring mode
            comparator.start_monitoring(args.duration, args.interval)

        # Generate final report
        print("\n📊 Generating performance report...")
        report = comparator.generate_report(args.output)

        # Print summary
        if report['summary']:
            print("\n" + "=" * 50)
            print("📈 PERFORMANCE SUMMARY")
            print("=" * 50)
            summary = report['summary']
            print(f"Processes monitored: {summary['total_processes_monitored']}")
            print(f"Total CPU usage: {summary['total_avg_cpu_percent']}%")
            print(f"Total memory usage: {summary['total_avg_memory_mb']}MB")
            print(f"Monitoring duration: {summary['monitoring_period_minutes']} minutes")

        # Print comparisons
        if report['comparison']:
            print("\n🆚 PERFORMANCE COMPARISON")
            print("=" * 50)
            for comp_name, comp_data in report['comparison'].items():
                print(f"\n{comp_name.replace('_', ' ').upper()}:")
                cpu_data = comp_data['cpu_efficiency']
                mem_data = comp_data['memory_efficiency']
                proc_data = comp_data['process_efficiency']

                print(f"  CPU Advantage: {cpu_data['cpu_advantage']} "
                      f"({cpu_data['cpu_savings_percent']:.1f}% savings)")
                print(f"  Memory Advantage: {mem_data['memory_advantage']} "
                      f"({mem_data['memory_savings_mb']:.1f}MB savings)")
                print(f"  Process Efficiency: {proc_data['process_advantage']}")

    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user")
    except Exception as e:
        logging.error(f"❌ Monitoring error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
