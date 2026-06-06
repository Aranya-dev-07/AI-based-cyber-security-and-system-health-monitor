import psutil
import time
import csv
import os
from datetime import datetime

#Allows the user to choose any available sensor if available 
def select_temperature_sensor():
    temps = psutil.sensors_temperatures()
    if not temps or all(len(v) == 0 for v in temps.values()):
        print("No temperature sensors found on this device. 😥")
        return None, None
    sensor_keys = list(temps.keys())
    if len(sensor_keys) == 1:
        selected_sensor_key = sensor_keys[0]
    else:
        print("Available temperature sensors:")
        for idx, sensor_name in enumerate(sensor_keys):
            print(f"{idx + 1}: {sensor_name} ({len(temps[sensor_name])} sub-sensors)")
        while True:
            try:
                choice = int(input(f"Select a sensor by number (1-{len(sensor_keys)}): "))
                if 1 <= choice <= len(sensor_keys):
                    selected_sensor_key = sensor_keys[choice - 1]
                    break
            except Exception:
                pass
            print("Invalid selection. Please try again.")
    sensors = temps[selected_sensor_key]
    if len(sensors) > 1:
        print(f"Available sub-sensors in '{selected_sensor_key}':")
        for idx, entry in enumerate(sensors):
            print(f"{idx + 1}: {entry.label or '(unnamed)'}")
        while True:
            try:
                sub_choice = int(input(f"Select a sub-sensor by number (1-{len(sensors)}): "))
                if 1 <= sub_choice <= len(sensors):
                    selected_sensor = sensors[sub_choice - 1]
                    break
            except Exception:
                pass
            print("Invalid selection. Please try again.")
    else:
        selected_sensor = sensors[0]
    return selected_sensor_key, selected_sensor.label

#Fetches some temperature data based on the user selection
def get_temperature(selected_key, selected_label):
    temps = psutil.sensors_temperatures()
    if not temps or selected_key not in temps: return None
    for entry in temps[selected_key]:
        if entry.label == selected_label or (not selected_label and not entry.label):
            return entry.current
    return None

#reading the existing csv collection file 
def get_run_number(csv_filename):
    run_num = 1
    if not os.path.exists(csv_filename):
        return run_num
    with open(csv_filename, 'r') as f:
        for line in f:
            if line.startswith("this is run"):
                try:
                    n = int(line.strip().split()[-1])
                    if n >= run_num:
                        run_num = n + 1
                except Exception:
                    pass
    return run_num

#The start Button
def main():
    print('Type "start" to begin collecting system metrics, or "stop" to exit.')
    command = input(">").strip().lower()
    if command != "start":
        print("Exiting")
        print("You must type 'start' to begin.")
        return

    # Sensor selection
    selected_sensor_key, selected_sensor_label = select_temperature_sensor()
    if selected_sensor_key is None:
        temp_sensor_available = False
    else:
        temp_sensor_available = True

    # Thresholds (customize as needed)
    CPU_THRESHOLD = 85    
    RAM_THRESHOLD = 80    
    DISK_THRESHOLD = 85   
    NET_THRESHOLD = 100*1024*1024  

    #Reporting data into the existing csv file
    csv_filename = "system_metrics_data.csv"
    run_num = get_run_number(csv_filename)
    headers = ['Timestamp', 'CPU (%)', 'RAM (%)', 'Disk (%)', 
               'Running Processes', 'Network Sent (MB)', 'Network Recv (MB)', 'Temp (degC)']

    stop_requested = False

#an alert system for resource usage and initializes a CSV log file for periodic system monitoring.
    def alert_engine(cpu, ram, disk, net_sent, net_recv):
        alerts = []
        if cpu > CPU_THRESHOLD:
            alerts.append(f"ALERT: CPU usage high ({cpu:.1f}%)")
        if ram > RAM_THRESHOLD:
            alerts.append(f"ALERT: RAM usage high ({ram:.1f}%)")
        if disk > DISK_THRESHOLD:
            alerts.append(f"ALERT: Disk usage high ({disk:.1f}%)")
        if (net_sent + net_recv) > NET_THRESHOLD:
            alerts.append(f"ALERT: Network spike (Sent+Recv > {NET_THRESHOLD/(1024*1024)} MB)")
        for msg in alerts:
            print(msg)

    if not os.path.exists(csv_filename):
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            f.write(f"this is run {run_num}\n")
            writer.writerow(headers)
    else:
        with open(csv_filename, 'a', newline='') as f:
            f.write(f"this is run {run_num}\n")
            writer = csv.writer(f)
            writer.writerow(headers)

    print("Collecting system metrics.....") 
    print("Type 'stop' to stop data collection.")
    
    last_net = psutil.net_io_counters()
    interval = 5 #The interval between each data collection in seconds
    
#Checks to stop the function     
    def input_listener():
        nonlocal stop_requested
        try:
            if os.name == 'nt':
                import msvcrt
                if msvcrt.kbhit():
                    line = input()
                    if line.strip().lower() == "stop":
                        stop_requested = True
            else:
                import select
                import sys
                i, _, _ = select.select([sys.stdin], [], [], 0)
                if i:
                    line = sys.stdin.readline()
                    if line.strip().lower() == "stop":
                        stop_requested = True
        except Exception:
            pass

#Collects the data and writes it to the CSV file.
    while not stop_requested:
    
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cpu_percent = psutil.cpu_percent(interval=None)
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        processes = len(psutil.pids())
        net_stats = psutil.net_io_counters()
        net_sent = net_stats.bytes_sent - last_net.bytes_sent
        net_recv = net_stats.bytes_recv - last_net.bytes_recv
        last_net = net_stats

        temp = get_temperature(selected_sensor_key, selected_sensor_label) if temp_sensor_available else "N/A"

        row = [
            timestamp, cpu_percent, ram_percent, disk_percent, processes, 
            round(net_sent/(1024*1024), 3), round(net_recv/(1024*1024), 3), temp
        ]

        with open(csv_filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)

        # Show alerts if needed
        alert_engine(cpu_percent, ram_percent, disk_percent, net_sent, net_recv)

        print(f"Metrics recorded at {timestamp}. Waiting {interval} seconds...")
        for i in range(interval * 10):
            time.sleep(0.1)
            input_listener()
            if stop_requested:
                break

    print("The user has stopped collecting the data.")
    print("Exiting...")
    print("Thank you for using the system health monitor! 😊")

#Ensures file is run when executed directly, not imported as a module.
if __name__ == "__main__":
    main()