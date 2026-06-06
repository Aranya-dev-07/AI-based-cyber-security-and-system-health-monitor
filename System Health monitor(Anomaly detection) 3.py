import psutil
import csv
import os
import time
from datetime import datetime

#sets the filename and thresholds for anomaly detection
FILENAME = 'system_metrics_data.csv'
THRESHOLDS = {
    'cpu': 90,         # CPU usage percent
    'ram': 90,         # RAM usage percent
    'disk': 90,        # Disk usage percent
    'network': 100*1024*1024, # 100MBps 
}

#Interval for measuring data 
interval = 5 

#Collects the data and stores them
def get_metrics():
    cpu = psutil.cpu_percent(interval=1)
    virtual_mem = psutil.virtual_memory()
    ram = virtual_mem.percent
    disk = psutil.disk_usage('/').percent
    net1 = psutil.net_io_counters()
    time.sleep(1)
    net2 = psutil.net_io_counters()
    net_sent = net2.bytes_sent - net1.bytes_sent
    net_recv = net2.bytes_recv - net1.bytes_recv
    procs = len(psutil.pids())
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cpu': cpu,
        'ram': ram,
        'disk': disk,
        'procs': procs,
        'net_sent': net_sent,
        'net_recv': net_recv,
    }
#THE ALERT ENGINE
def alert_engine(metrics):
    alerts = []
    if metrics['cpu'] > THRESHOLDS['cpu']:
        alerts.append(f"CPU usage high: {metrics['cpu']}%")
    if metrics['ram'] > THRESHOLDS['ram']:
        alerts.append(f"RAM usage high: {metrics['ram']}%")
    if metrics['disk'] > THRESHOLDS['disk']:
        alerts.append(f"Disk usage high: {metrics['disk']}%")
    if metrics['net_sent'] > THRESHOLDS['network'] or metrics['net_recv'] > THRESHOLDS['network']:
        alerts.append(f"Network spike detected (send: {metrics['net_sent']} bytes/sec, recv: {metrics['net_recv']} bytes/sec)")
    for alert in alerts:
        print("ALERT:", alert)

#To keep track of the number of runs 
def get_next_run_number():
    if not os.path.exists(FILENAME):
        return 1
    run_num = 1
    with open(FILENAME, 'r', newline='') as f:
        for row in csv.reader(f):
            if row and row[0].startswith('this is run '):
                try:
                    n = int(row[0].split(' ')[-1])
                    if n >= run_num:
                        run_num = n + 1
                except:
                    continue
    return run_num

#Defines the csv file to read data
def write_header_if_needed():
    if not os.path.exists(FILENAME):
        with open(FILENAME, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["this is run 1"])
            writer.writerow(['timestamp','cpu_percent','ram_percent','disk_percent','running_procs','net_sent','net_recv'])

#These are defined to continuously append data 
def append_run_tag(run_n):
    if os.path.exists(FILENAME):
        with open(FILENAME, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([f"this is run {run_n}"])
            writer.writerow(['timestamp','cpu_percent','ram_percent','disk_percent','running_procs','net_sent','net_recv'])

def append_metrics(metrics):
    with open(FILENAME, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            metrics['timestamp'],
            metrics['cpu'],
            metrics['ram'],
            metrics['disk'],
            metrics['procs'],
            metrics['net_sent'],
            metrics['net_recv']
        ])

#Allows the user to start and stop data collection.
def main():
    global interval
    write_header_if_needed()
    run_num = get_next_run_number()
    if run_num > 1:
        append_run_tag(run_num)
    print('Type "start" to begin data collection, or "stop" to exit.')
    print(f"Current interval for metrics collection is set to {interval} seconds.")
    print('If you want to change the interval, type the number of seconds and press Enter, or just press Enter to keep current value.')
    
    inp = input(f"Set new interval in seconds (current: {interval}): ").strip()
    if inp:
        try:
            val = int(inp)
            if val > 0:
                interval = val
                print(f"Interval changed to {interval} seconds.")
            else:
                print("Interval must be a positive integer. Using default.")
        except ValueError:
            print("Invalid input. Using default interval.")

    # Awaiting user to type 'start'
    while True:
        cmd = input('> ').strip().lower()
        if cmd == "start":
            print(f"Starting system health data collection (This is run {run_num})...")
            break
        elif cmd == "stop":
            print("The user has stopped collecting the data")
            print("Exitting...")
            print("Thank you for using the system health monitor. Goodbye! 😀")
            return

    collecting = True

    try:
        while collecting:
            metrics = get_metrics()
            append_metrics(metrics)
            alert_engine(metrics)
            
            start_time = time.time()
            elapsed = 0
            while elapsed < interval:
                remaining = interval - elapsed
                prompt = f"(Type 'stop' and Enter to end data collection, or just Enter to continue. Next check in {remaining}s): "
                user_input = input(prompt).strip().lower()
                if user_input == "stop":
                    print("The user has stopped collecting the data")
                    collecting = False
                    break
                time.sleep(1)
                elapsed = int(time.time() - start_time)
    except KeyboardInterrupt:
        print("The user has stopped collecting the data")
        print("Exiting gracefully...")
        print("Thank you for using the system health monitor. Goodbye! 😀")

#Executes the main function when the script is run directly not when loaded
if __name__ == '__main__':
    main()