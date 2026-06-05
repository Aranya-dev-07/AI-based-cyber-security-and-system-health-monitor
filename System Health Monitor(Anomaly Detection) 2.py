import psutil
import csv
import time
import os
import sys
from datetime import datetime

# Thresholds for alert system
CPU_THRESHOLD = 80      # percent
RAM_THRESHOLD = 80      # percent
DISK_THRESHOLD = 80     # percent
NET_THRESHOLD = 1e7     # 10 MB/s in bytes

def select_temperature_sensor():
    # Try to get all temperatures
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            print("No temperature sensors found on this system. Temperature metrics will be skipped.")
            return None, None
        # Flatten all labels with entries
        sensors = []
        for sensor_type, entries in temps.items():
            for entry in entries:
                sensors.append((sensor_type, entry.label if entry.label else "N/A"))
        sensors = list(set(sensors))  # unique (type, label)
        if not sensors:
            print("No valid sensors with entries found.")
            return None, None
        if len(sensors) == 1:
            print(f"Only one sensor found: {sensors[0][0]} ({sensors[0][1]})")
            return sensors[0]
        print("Available sensors:")
        for i, (stype, label) in enumerate(sensors):
            print(f"[{i}] {stype} - {label}")
        while True:
            try:
                idx = int(input("Select sensor number for temperature monitoring: "))
                if 0 <= idx < len(sensors):
                    return sensors[idx]
                else:
                    print("Invalid input, try again.")
            except Exception:
                print("Please enter a valid number.")
    except Exception as e:
        print(f"Exception when fetching sensors: {e}")
        return None, None

def get_temperature(sensor_type, label):
    temps = psutil.sensors_temperatures()
    if sensor_type and sensor_type in temps:
        for entry in temps[sensor_type]:
            entry_label = entry.label if entry.label else "N/A"
            if entry_label == label:
                return entry.current
    return None

def get_run_number(csv_file):
    if not os.path.exists(csv_file):
        return 1
    # Look for previous runs, find highest run number used in the file
    last_run = 0
    with open(csv_file, "r") as f:
        for line in f:
            if line.startswith("this is run "):
                try:
                    n = int(line.strip().split("this is run ")[1])
                    if n > last_run:
                        last_run = n
                except Exception:
                    continue
    return last_run + 1

def log_alerts(metrics, net_diff):
    alerts = []
    if metrics['cpu_percent'] > CPU_THRESHOLD:
        alerts.append(f"ALERT: CPU usage high ({metrics['cpu_percent']}%)")
    if metrics['virtual_memory_percent'] > RAM_THRESHOLD:
        alerts.append(f"ALERT: RAM usage high ({metrics['virtual_memory_percent']}%)")
    if metrics['disk_percent'] > DISK_THRESHOLD:
        alerts.append(f"ALERT: Disk usage high ({metrics['disk_percent']}%)")
    if net_diff is not None and net_diff > NET_THRESHOLD:
        alerts.append(f"ALERT: Network spike detected ({net_diff/1e6:.2f} MB/s)")
    return alerts

def get_running_processes():
    process_list = []
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        try:
            process_list.append(f"{proc.info['pid']}:{proc.info['name']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return '|'.join(process_list)

def collect_and_store_metrics(csv_file, sensor_type, sensor_label, run_num):
    fieldnames = [
        'timestamp', 'cpu_percent', 'virtual_memory_percent', 'available_ram_MB',
        'disk_percent', 'used_disk_GB', 'running_processes', 'net_sent_MBps', 'net_recv_MBps', 'temperature_C'
    ]

    # If file does not exist, create and write header
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            csvfile.write(f"this is run {run_num}\n")
            writer.writeheader()
        else:
            csvfile.write(f"this is run {run_num}\n")

        prev_net = psutil.net_io_counters()
        prev_sent = prev_net.bytes_sent
        prev_recv = prev_net.bytes_recv

        print("Collecting system health data. Press Ctrl+C to stop.")
        try:
            while True:
                # Block comment: This is where the interval of 5 seconds is defined for periodic data collection.
                # The time.sleep(5) call ensures metrics are sampled every 5 seconds, as required.
                time.sleep(5)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cpu_percent = psutil.cpu_percent(interval=None)
                virtual_memory = psutil.virtual_memory()
                disk_usage = psutil.disk_usage('/')
                running_processes = get_running_processes()
                
                net = psutil.net_io_counters()
                net_sent_MBps = (net.bytes_sent - prev_sent) / 5 / 1e6
                net_recv_MBps = (net.bytes_recv - prev_recv) / 5 / 1e6
                net_diff = max(net.bytes_sent - prev_sent, net.bytes_recv - prev_recv) / 5

                prev_sent = net.bytes_sent
                prev_recv = net.bytes_recv

                temp = None
                if sensor_type:
                    temp = get_temperature(sensor_type, sensor_label)

                row = {
                    'timestamp': timestamp,
                    'cpu_percent': cpu_percent,
                    'virtual_memory_percent': virtual_memory.percent,
                    'available_ram_MB': round(virtual_memory.available / 1e6, 2),
                    'disk_percent': disk_usage.percent,
                    'used_disk_GB': round(disk_usage.used / 1e9, 2),
                    'running_processes': running_processes,
                    'net_sent_MBps': round(net_sent_MBps, 3),
                    'net_recv_MBps': round(net_recv_MBps, 3),
                    'temperature_C': temp if temp is not None else "N/A"
                }
                writer.writerow(row)
                csvfile.flush()

                # Alert engine
                alerts = log_alerts(row, net_diff)
                for alert in alerts:
                    print(alert)
        except KeyboardInterrupt:
            print("Data collection stopped.")
            print("Exitting...")
            print("Thank you for using the system health monitor. Goodbye! 😀")

def main():
    csv_file = "system_metrics_data.csv"
    run_num = get_run_number(csv_file)
    sensor_type, sensor_label = select_temperature_sensor()
    collect_and_store_metrics(csv_file, sensor_type, sensor_label, run_num)

if __name__ == "__main__":
    main()