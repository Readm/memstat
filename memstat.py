import psutil
import os
import sys
import math
import time
import logging
import subprocess
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
background_mem_info = []
max_process_name_cnt = dict()
time_seconds = 60 # 0 for unlimited
time_set = False
interval_microseconds = 1000
silent = False
target_commands = []
target_users = []
target_pid = 0
filters_and = True
with_background = False
record = ""

logger = logging.getLogger("mem_stat")
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '[mem stat] %(levelname)5s - %(asctime)s: %(message)s',
    datefmt='%H:%M:%S')
console_handler.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

def get_self_and_command_args():
    args = sys.argv
    cmd_args = []
    self_args = []
    after_double_dash = False
    
    for arg in args:
        if arg == "--":
            after_double_dash = True
            continue
        
        if after_double_dash:
            cmd_args.append(arg)
        else:
            self_args.append(arg)
    
    return self_args, cmd_args

def create_directories():
    if not os.path.exists(figure_directory):
        os.makedirs(figure_directory)
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

def plot_histogram(data, title, figure_directory, background = None):
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
    if background:
        plt.hist(background, bins=bins, color='grey', edgecolor='black', label="Background")
    plt.hist(data, bins=bins, color='skyblue', edgecolor='black')
    plt.xscale('log')  # Set x-axis scale to logarithmic
    plt.xlabel(title + " (Byte)")  
    plt.xlim(min_value, max_value)  
    # plt.gca().xaxis.set_major_formatter(ScalarFormatter(useMathText=False))
    plt.ylabel('Process Count')
    plt.title(f'Histogram of {item_des[title]}')
    if background:
        plt.legend()
    if sum(data) == 0:
        plt.title(f'Histogram of {item_des[title]} (Empty)')
    plt.grid(True, which="both", ls="--")
    plt.savefig(os.path.join(figure_directory, f'{title}_histogram.png'))
    plt.close()

def is_descendant_of(process_pid, ancestor_pid):
    logger.debug(f"search ancestor pid from {process_pid} -> {ancestor_pid}")
    pid = process_pid
    while True:
        logger.debug(f"pid = {pid}")
        if ancestor_pid == pid:
            return True
        else:
            if pid==0: return False
            pid = psutil.Process(pid).ppid()

def filter_by_command(process):
    if not target_commands: return filters_and
    for name in target_commands:
        if name == os.path.basename(process.cmdline()[0]):
            return True
    return False
    
def filter_by_user(process):
    if not target_users: return filters_and
    for name in target_users:
        if name == process.username():
            return True
    return False

def filter_by_pid(process):
    if not target_pid: return filters_and
    return is_descendant_of(process.pid, target_pid)      

def filter_all(process):
    if not target_pid and not target_users and not target_commands:
        return True
    if filters_and:
        return filter_by_command(process) and filter_by_user(process) and filter_by_pid(process)
    else:
        return filter_by_command(process) or filter_by_user(process) or filter_by_pid(process)
    
def sample_once():
    '''Return False if nothing sampled'''
    global record, silent
    all_processes = psutil.process_iter()
    record += f'Sample @ {datetime.now()}'
    max_memory = 0
    max_memory_name = ''
    sample_cnt = 0
    for process in all_processes:
        try:
            mem_info = process.memory_info()
            m = [mem_info.__getattribute__(i) for i in items]
            record += f" PID: {process.pid}, Mem_info: {mem_info}\n"
            if sum(m) == 0: continue
            if with_background:
                background_mem_info.append(mem_info)
            if not filter_all(process): continue
            logger.debug(f"PID:{process.pid}, USER:{process.username()}, CMD:{process.cmdline()[0]}")
            # log max
            if mem_info.rss > max_memory: max_memory_name = process.cmdline()[0]
            max_memory = max(max_memory, mem_info.rss)

            process_mem_info.append(mem_info)
            sample_cnt += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    global max_process_name_cnt
    if max_memory_name not in max_process_name_cnt.keys():
        max_process_name_cnt[max_memory_name] = 0
    max_process_name_cnt[max_memory_name] += 1
    if not silent: logger.info(f"Sampling, total {len(process_mem_info)} samples.")
    if sample_cnt == 0:
        return False
    else:
        return True


def print_usage():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
            print(readme_content)
    except FileNotFoundError:
        print("README.md not found.")

def drawing():
    logger.info(f"\nStart drawing figures, DON'T interrupt!")
    if not process_mem_info:
        logger.error(f"Nothing sampled, exit")
        exit(1)
    for title in items:
        data = [p.__getattribute__(title) for p in process_mem_info]
        background = [p.__getattribute__(title) for p in background_mem_info] if with_background else None
        plot_histogram(data, title, figure_directory, background)
        with open(os.path.join(log_directory, "mem_stat.log"), "w+") as f:
            f.write(record + "\nMax mem process count:" + str(max_process_name_cnt))

if __name__ == "__main__":
    args, cmds = get_self_and_command_args()
    if "-h" in args or "--help" in args:
        print_usage()
        sys.exit(0)
    if "--time" in args:
        try:
            a_index = args.index("--time")
            time_arg = args[a_index + 1]
            time_seconds = int(time_arg)
            time_set = True
        except (IndexError, ValueError):
            print("Invalid time argument.")
    if "--interval" in args:
        try:
            a_index = args.index("--interval")
            interval_arg = args[a_index + 1]
            interval_microseconds = int(interval_arg)
        except (IndexError, ValueError):
            print("Invalid interval argument.")
    if "--filter-command" in args:
        try:
            a_index = args.index("--filter-command")
            filter_commands = args[a_index + 1]
            target_commands = filter_commands.split(',')
        except (IndexError, ValueError):
            print("Invalid filter-command argument.")
    if "--filter-user" in args:
        try:
            a_index = args.index("--filter-user")
            filter_users = args[a_index + 1]
            target_users = filter_users.split(',')
        except (IndexError, ValueError):
            print("Invalid filter-user argument.")
    if "--silent" in args:
        silent = True
    if "--filter-and" in args:
        filters_and = True
    if "--filter-or" in args:
        filters_and = False
    if "--background" in args:
        with_background = True
    record += str(sys.argv) + '\n'

    create_directories()
    if cmds: # monitor cmd, else monitor all
        process = subprocess.Popen(cmds)
        assert not target_commands and not target_users, "No filter supported in command mode."
        if not time_set: time_seconds = 0
        target_pid = process.pid
        logger.info(f"Start sampling PID {target_pid}, cmd: {' '.join(cmds)}")
    logger.info(f"Profiling time: {'in '+str(time_seconds)+' seconds' if time_seconds else 'continuously'}, every {interval_microseconds} ms. Press Ctrl+C to end sampling.")
    try:
        start_time = time.time()
        while True:
            sampled = sample_once()
            if not sampled and cmds: break # break when cmd ends
            time.sleep(interval_microseconds/1000)
            if time_seconds and time.time() - start_time >= time_seconds:
                break
    except KeyboardInterrupt:
        pass
    finally:
        drawing()

