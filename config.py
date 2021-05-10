# coding=utf-8

# config about memory
memory_management_mode = 'p'
memory_page_size = 1024
memory_page_number = 16
memory_physical_page_number = 8

# config about process scheduling
priority = True
preemptive = True
time_slot = 1
cpu_num = 1
printer_num = 1

# config about storage
storage_block_size = 512
storage_track_num = 200
storage_sec_num = 12

seek_algo = 'FCFS'  # from: {FCFS, SSTF, SCAN, C_SCAN, LOOK, C_LOOK}
