# MemoryProfile

+ Usage1: Profile all processes in the OS.
    + start: `python3 sysmemstat.py`
    + end: 
        + Press Ctrl+C, then wait the data processing.
        + After 60s the profiling automatically ens, if not `-t` set.
+ Usage2: Profile one command, including all child processes.
    + start: `python3 sysmemstat.py -- command`
    + end: 
        + Press Ctrl+C, then wait the data processing.
        + When the cammand ends, the profiling automatically ens.
+ Arguments:
    + `-h` or `--help`: Show doc.
    + `--time s`: Set the profiling time as `s` seconds. (Default: 60), set 0 for continuous sample, until Ctrl+C pressed.
    + `--interval m`: Set the profiling interval as `m` microseconds. (Default: 1000)
    + `--silent`: Silent mode, no info about all sample points.
    + `--filter-command cmd1,cmd2`: Filter by command name, seperated by comma.
    + `--filter-user user1,user2`: Filter by user name, seperated by comma.
    + `--filter-and`: Each process should pass all filter (Default).
    + `--filter-or`: Each process is required to pass only one filter.
    + `--background`: Add OS background info in figures.
