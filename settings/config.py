# coding=utf-8

'''
config参数，均为私有属性封装并保护起来，通过getter访问
'''
class Config(object):
    # about memory
    memory_management_mode = 'p'
    memory_page_size = 1024
    memory_page_number = 16
    memory_physical_page_number = 8

    # about process scheduling
    priority = True
    preemptive = True
    time_slot_conf = 0.1
    cpu_num = 1
    printer_num_conf = 1

    # about storage
    storage_block_size = 512
    storage_track_num = 200
    storage_sec_num = 12

    seek_algo = 'FCFS'  # from: {FCFS, SSTF, SCAN, C_SCAN, LOOK, C_LOOK}
