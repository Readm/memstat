import psutil
import os
import math
import time
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

items = ['rss', 'vms', 'shared', 'text', 'lib', 'data', 'dirty']
item_des = {
    'rss' : "Resident Set Size",
    'vms' : "Virtual Memory Size",
    'shared' : "Shared Memory",
    'text' : "Text Memory",
    'lib'  : "Library Memory",
    'data' : "Data Memory",
    'dirty' : "Dirty Memory"
}

current_path = os.path.dirname(os.path.abspath(__file__))
figure_directory = os.path.join(current_path, 'figures')
log_directory = os.path.join(current_path, 'logs')
process_mem_info = []
max_process_name_cnt = dict()
log = ""

def create_directories():
    if not os.path.exists(figure_directory):
        os.makedirs(figure_directory)
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

def plot_histogram(data, title, figure_directory):
    plt.figure()
    max_value = float(max(data))
    if max_value == 0:
        max_value = 1  # Avoid zero max_value
    n = math.ceil(math.log10(max_value))
    max_value = 10 ** n
    min_value = float(min(data))
    if min_value == 0:
        min_value = 1
    n = math.ceil(math.log10(min_value))
    min_value = 10 ** (n-1)
    bins = np.geomspace(1, max_value, num=50, endpoint=True)
    plt.hist(data, bins=bins, color='skyblue', edgecolor='black')
    plt.xscale('log')  # Set x-axis scale to logarithmic
    plt.xlabel(title + " (Byte)")  
    plt.xlim(min_value, max_value)  
    # plt.gca().xaxis.set_major_formatter(ScalarFormatter(useMathText=False))
    plt.ylabel('Process Count')
    plt.title(f'Histogram of {item_des[title]}')
    if sum(data) == 0:
        plt.title(f'Histogram of {item_des[title]} (Empty)')
    plt.grid(True, which="both", ls="--")
    plt.savefig(os.path.join(figure_directory, f'{title}_histogram.png'))
    plt.close()

def sample_once():
    global log
    all_processes = psutil.process_iter()
    log += f'Sample @ {datetime.now()}'
    max_memory = 0
    max_memory_name = ''
    for process in all_processes:
        try:
            parent_pid = process.ppid()
            mem_info = process.memory_info()
            m = [mem_info.__getattribute__(i) for i in items]
            if sum(m) == 0: continue
            if mem_info.rss > max_memory: max_memory_name = process.cmdline()[0]
            max_memory = max(max_memory, mem_info.rss)
            log += f"PID: {process.pid}, Mem_info: {mem_info}\n"
            process_mem_info.append(mem_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    global max_process_name_cnt
    if max_memory_name not in max_process_name_cnt.keys():
        max_process_name_cnt[max_memory_name] = 0
    max_process_name_cnt[max_memory_name] += 1
    print(f"Sampling, total {len(process_mem_info)} samples, press Ctrl+C to end sampling.")

    
if __name__ == "__main__":
    create_directories()
    try:
        while True:
            sample_once()
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"Start drawing figures, DON'T interrupt!")
        for title in items:
            plot_histogram([p.__getattribute__(title) for p in process_mem_info], title, figure_directory)
            with open(os.path.join(log_directory, "mem_stat.log"), "w+") as f:
                f.write(log + str(max_process_name_cnt))

