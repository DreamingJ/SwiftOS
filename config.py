# coding=utf-8
#import const
#const = Const()

# config about memory
option="LRU" #from{LRU,FIFO}

frame_size = 1024
storage_mode = 'ps' #from {ps页式分配存储方式,cs连续分配存储方式}
page_size=1024
page_total=8
frame_size=1024                 
frame_total=6


# config about process scheduling

priority_conf = True
preemptive = True
time_slot_conf = 1
cpu_num = 1
printer_num_conf = 1


# config about storage

storage_block_size = 512
storage_track_num = 200
storage_sec_num = 12
seek_algo = 'FCFS'  # from: {FCFS, SSTF, SCAN, C_SCAN, LOOK, C_LOOK}
