import time
from config import *
import logging

class Printer(object):
    def __init__(self):
        self.printer_num = printer_num_conf
        logging.basicConfig(level=logging.INFO,
                    filename='log.txt',
                    filemode='w', # w就是写模式，a是追加模式
                    format='%(asctime)s - %(message)s')


    def print_resource_status(self):
        """ 获取设备资源状态 """
        if self.printer_num == printer_num_conf:
            print(f'No Printer is using,there are {self.printer_num} Printer is free')
        else:
            print(f'{self.printer_num} Printer is using')


    def io_device_handler(self, waiting_queue, io_completion):
        while True:
            # 从waiting队列调度任务进行io
            if waiting_queue:
                pid = waiting_queue[0][0]
                wait_time = waiting_queue[0][0]
                # 处理打印机任务
                waiting_queue.pop(0)
                self.printer_num -= 1
                time.sleep(wait_time)

                # io完成
                self.printer_num += 1
                logging.info(f'[pid {pid}] process I/O successfully.')
                io_completion(pid)        


class Disk(object):
    pass