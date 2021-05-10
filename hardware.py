# coding=utf-8
import datetime
import time


class Hardware:
    def __init__(self, resource_num):
        self.free_time = datetime.datetime.now() + datetime.timedelta(days=365)
        self.free_resource = resource_num  # Resource number
        self.resource_num = resource_num
        self.running_queue = []

class Timer:
    def __init__(self):
        self.start_time = datetime.datetime.now()
        
        self.time_slot = 10  #时间片间隙

    def timeout(self):
        print ("timeout!")

    def print_current_time(self):
        self.current_time = datetime.datetime.now()
        print(self.current_time)

class  Register:
    def __init__(self):
        self.PSW = 0 #1代表进行中断
        self.IR = 0
        self.PC = 0
        self.DR = 0
        self.AR = 0 

class CPU:
    def __init__(self):
        pass
    def cpu