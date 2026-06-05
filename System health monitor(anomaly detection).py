import psutil
import csv
import time
import threading
import sys

#For monitoring the temperature 
try:
    import psutil
    psutil_sensors_temp = psutil.sensors_temperatures
except (ImportError, AttributeError):
    psutil_sensors_temp = None

from datetime import datetime

#It sets the Adjustable thresholds for CPU, RAM, Disk usage and network spikes
THRESHOLDS = {
    'cpu': 80,       
    'ram': 80,       
    'disk': 90,     
    'net_sent': 10*1024*1024,   
    'net_recv': 10*1024*1024,   
}
#Function defined to choose a sensor 
def select_sensor():
    if psutil_sensors_temp is None:
        print("Temperature sensors are not supported on this system.")
        return None, None

    temps = psutil.sensors_temperatures(fahrenheit=False)
    if not temps:
        print("No temperature sensors found.")
        return None, None

    if len(temps) == 1:
        key = list(temps.keys())[0]
        print(f"Detected one sensor group: {key}")
        return key, temps[key]
    else:
        print("Available sensor groups:")
        for idx, key in enumerate(temps.keys()):
            print(f"{idx+1}: {key}")
        while True:
            try:
                choice = int(input("Select sensor group by number: ")) - 1
                if 0 <= choice < len(temps):
                    key = list(temps.keys())[choice]
                    return key, temps[key]
            except ValueError:
                pass
            print("Invalid selection. Please try again.")

#Function defined to get the temperature of the system
def get_temperature(sensor_group):
    if psutil_sensors_temp is None or sensor_group is None:
        return "N/A"
    temps = psutil.sensors_temperatures(fahrenheit=False)
    sensors = temps.get(sensor_group, [])
   
    if sensors:
        return sensors[0].current
    return "N/A"

#It checks all metrics against the defined thresholds and generates alerts if any metric exceed its threshold
def alert_engine(stats, last_net):
    alerts = []
    if stats['cpu_usage'] > THRESHOLDS['cpu']:
        alerts.append(f"ALERT: High CPU usage: {stats['cpu_usage']}%")
    if stats['memory_percent'] > THRESHOLDS['ram']:
        alerts.append(f"ALERT: High RAM usage: {stats['memory_percent']}%")
    if stats['disk_percent'] > THRESHOLDS['disk']:
        alerts.append(f"ALERT: High Disk usage: {stats['disk_percent']}%")

    net_sent_spike = stats['bytes_sent'] - last_net['sent']
    net_recv_spike = stats['bytes_recv'] - last_net['recv']
    if net_sent_spike > THRESHOLDS['net_sent']:
        alerts.append(f"ALERT: Network sent spike: {net_sent_spike} bytes")
    if net_recv_spike > THRESHOLDS['net_recv']:
        alerts.append(f"ALERT: Network recv spike: {net_recv_spike} bytes")
    return alerts, {'sent': stats['bytes_sent'], 'recv': stats['bytes_recv']}

#This returns a formated list of 5 most resource heavy processes
def collect_processes(top_n=5):
    
    processes = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
   
    top = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:top_n]
    process_str = "; ".join([f"{proc['name']}({proc['pid']}):CPU%={proc['cpu_percent']} RAM%={proc['memory_percent']}" for proc in top])
    return process_str

#This function initializes the monitoring system by selecting sensors, creating a timestamped CSV log file, defining data columns, and setting up network tracking
def main():
    sensor_group, _ = select_sensor()
    FILENAME = f"system_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # CSV headers
    headers = [
        "timestamp",
        "cpu_usage_percent",
        "ram_usage_percent",
        "disk_usage_percent",
        "temperature_c",
        "bytes_sent",
        "bytes_recv",
        "alerts",
        "top_processes"
    ]

    last_net = {'sent': 0, 'recv': 0}

#This stores the needed metrics in a csv file 
    with open(FILENAME, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        print(f"Collecting system health data every 5 seconds. (Data is being stored to {FILENAME})")
        if sensor_group is None:
            print("Temperature data will be unavailable.")
        try:
            while True:
                stats = {}
                stats['cpu_usage'] = psutil.cpu_percent(interval=1)
                stats['memory_percent'] = psutil.virtual_memory().percent
                stats['disk_percent'] = psutil.disk_usage('/').percent

                temp = get_temperature(sensor_group)
                stats['temperature'] = temp

                net_io = psutil.net_io_counters()
                stats['bytes_sent'] = net_io.bytes_sent
                stats['bytes_recv'] = net_io.bytes_recv

                top_processes = collect_processes()

                alerts, last_net = alert_engine(stats, last_net)

                
                for alert in alerts:
                    print(alert)

                row = [
                    datetime.now().isoformat(),
                    stats['cpu_usage'],
                    stats['memory_percent'],
                    stats['disk_percent'],
                    temp,
                    stats['bytes_sent'],
                    stats['bytes_recv'],
                    '|'.join(alerts),
                    top_processes
                ]
                writer.writerow(row)
                csvfile.flush()
                time.sleep(4)  
        except KeyboardInterrupt:
            print("\nData collection stopped by user (Ctrl+C).")

#This ensures the function is executed only when the script is run directly, not when imported as a module
if __name__ == "__main__":
    main()