#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import copy
import threading
#import config
from memory_manager import MemoryManager


class PCB(object):
    """ ProcessControlBlock
    Atrributes:
        pid,pname,parentid,priority,create_time,status,
        tasklist: 该进程待执行的任务
        msize: 该进程所占用的内存大小
    """
    def __init__(self, pid, pname, priority, content, msize):
        self.pid = pid
        self.pname = pname
        self.priority = priority  # 0 is higher than 1
        self.msize = msize
        self.parent_id = -1
        self.child_pid_list = []    
        self.create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        self.status = 'ready'

        self.tasklist = []
        for task in content:
            info = str.split(task)  
            if len(info) > 1:
                if info[0] == 'cpu':
                    info[1] = float(info[1])
                else:
                    info[1] = int(info[1])
            self.tasklist.append(info)  # example: [[printer, 18], [cpu, 170]]
        self.current_task = 0


class ProcessManager(object):
    """ Provide functions to manage process"""
    def __init__(self, memory_manager,time_slot_conf,priority_conf,printer_num_conf):
        """ 
        Args:
            pid_no: 下个进程的序号
            pcblist: 被管理进程的PCB
            ready_queue: 就绪队列，分为三个优先级
            waiting_queue:等待队列
            p_running：正在运行的进程，引用pcb，同一时间只有一个
            memory_manager: 每个进程所对应的内存及其管理器
            mem_of_pid：每个进程所对应的内存号
        """
        self.pid_no = 0
        self.pcblist = []
        self.ready_queue = [[] for i in range(3)]
        self.waiting_queue = []
        self.p_running = None
        self.is_running = False
        self.memory_manager=memory_manager
        self.time_slot=time_slot_conf
        self.priority=priority_conf
        self.printer_num = printer_num_conf
        self.mem_of_pid = {}

    def create(self, exefile):
        """ 打开程序文件创建进程 """
        if exefile['type'][0] != 'e':
            self.error_handler('exec')
        else:
            mem_no = self.memory_manager.allocate_memory(self.pid_no, int(exefile['size'])) 
            if mem_no == -1:
                self.error_handler('mem')
            else:
                pcb = PCB(self.pid_no, exefile['name'], exefile['priority'], exefile['content'], int(exefile['size']))
                self.pcblist.append(pcb)
                self.mem_of_pid[pcb.pid] = mem_no
                print(f'[pid {pcb.pid}] process created successfully.')
                self.ready_queue[exefile['priority']].append(pcb.pid)
                self.pid_no += 1

    def fork(self):
        """ 创建子进程 """
        child_msize = self.p_running.msize
        mem_no = self.memory_manager.allocate_memory(self.pid_no, child_msize) 
        if mem_no == -1:
            self.error_handler('mem')
        else:            
            # self.p_running.current_task += 1
            # 初始化子进程pcb
            child_pcb = copy.deepcopy(self.p_running) 
            child_pcb.pid = self.pid_no
            child_pcb.parent_id = self.p_running.pid
            child_pcb.create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            # 子进程下一task
            child_pcb.current_task += 1

            self.pcblist.append(child_pcb)
            self.ready_queue[child_pcb.priority].append(child_pcb.pid)
            self.pid_no += 1
            self.p_running.child_pid_list.append(child_pcb)
            sys.stdout.write('\033[2K\033[1G\033[3D')  # to remove extra output \$
            print(f'[pid {child_pcb.pid}] process forked successfully by [pid {child_pcb.parent_id}].')

    def dispatch(self):
        """ 调度进程，ready->running """
        self.p_running = None
        for level in range(0, len(self.ready_queue)):
            # 就绪队列不为空
            if self.ready_queue[level]:
                self.p_running = self.pcblist[self.ready_queue[level][0]]
                self.ready_queue[level].pop(0)
                self.p_running.status = 'running'
                break

    def timeout(self):
        """ 时间片用尽，running->ready """
        time.sleep(self.time_slot)
        if self.p_running:
            # 进程进入就绪队列继续等待执行
            self.p_running.status = 'ready'
            level = self.p_running.priority
            self.ready_queue[level].append(self.p_running.pid)

    def io_wait(self):
        """ 等待io事件，进程阻塞，running->waiting """
        self.p_running.status = 'waiting'
        io_time = self.p_running.tasklist[self.p_running.current_task][1]
        # waiting queue： [[pid1, time], [pid2, time]]
        self.waiting_queue.append([self.p_running.pid, io_time])


    def io_completion(self, pid):
        """ io完成，进程被唤醒，waiting->ready """
        self.printer_num += 1
        print(f'[pid {pid}] process I/O successfully.')
        if self.keep_next_task(pid) == True:
            self.pcblist[pid].status = 'ready'
            level = self.pcblist[pid].priority
            self.ready_queue[level].append(pid)

    def io_interrupt(self,pid):
        """  """


    def kill(self, pid):
        """ kill进程，释放所属资源. 考虑和run守护进程的互斥 """
        if pid not in [pcb.pid for pcb in self.pcblist]:
            self.error_handler('kill_nopid', pid)
        else:
            status = self.pcblist[pid].status
            if status == 'terminated':
                self.error_handler('kill_already', pid)
            else:
                if status == 'ready':
                    level = self.pcblist[pid].priority
                    self.ready_queue[level].remove(pid)
                elif status == 'running':
                    self.p_running = None
                elif status == 'waiting':
                    self.waiting_queue.remove(pid)
                elif status == 'waiting(Printer)':
                    self.io_completion(pid)
                self.pcblist[pid].status = 'terminated'
                # 释放内存资源
                self.memory_manager.free_memory(pid)
                

    def keep_next_task(self, pid):
        # 若当前是进程的最后一条task，转为结束态
        if self.pcblist[pid].current_task == len(self.pcblist[pid].tasklist)-1 :
            if(self.memory_manager.free_memory(pid)):
                # 从就绪队列取出
                self.ready_queue[self.pcblist[pid].priority].remove(pid)
                self.pcblist[pid].status = 'terminated'
                print(f'[Pid #{pid}] finished.')
            else:
                # 该进程对应的内存空间已被释放
                print("Failed to free, the memory of [Pid %d] has been freed." % pid)
            return False
        else:   # 继续下一个task
            self.pcblist[pid].current_task += 1
            return True

    def print_process_status(self):
        """ 获取当前进程状态 """
        running = False
        for pro in self.pcblist:
            if pro.status != 'terminated':
                print("[pid #%5d] name: %-10s status: %-20s create_time: %s" % (pro.pid, pro.pname, pro.status, pro.create_time))
                running = True
        if not running:
            print("No process is running currently")

    def print_resource_status(self):
        """ 获取设备资源状态 """
        if self.printer_num == printer_num_conf:
            print(f'No Printer is using,there are {self.printer_num} Printer is free')
        else:
            print(f'{self.printer_num} Printer is using')

    def input_handler(self):
        """ 处理命令行输入 """
        while True:
            s = input("\$").split()
            if s[0] == 'ps':
                self.print_process_status()
            elif s[0] == 'rs':
                self.print_resource_status()
            elif s[0] == 'kill':
                self.kill(int(s[1]))
            elif s[0] == 'exec':
                # 需配合文件管理模块
                exefile = self.file_manager.get_file(file_path=s[1], seek_algo=seek_algo)
                self.create(exefile)
            else:
                print('command not found: %s' % s[0])


    def io_device_handler(self):
        """ 守护线程，模拟IO设备运行 """
        while True:
            # 从waiting队列调度任务进行io
            if self.waiting_queue:
                pid = self.waiting_queue[0][0]
                wait_time = self.waiting_queue[0][0]
                # TODO waitingqueue太长，remove元素
                self.waiting_queue.pop(0)
                self.pcblist[pid].status = "waiting(Printer)"
                self.printer_num -= 1
                time.sleep(wait_time)
                # io完成
                self.io_completion(pid)

    def start_manager(self):
        """ 主逻辑，启动模块并运行 """
        self.is_running = True
        while self.is_running:
            self.dispatch()
            if self.p_running:
                # current不能为-1
                task = self.p_running.tasklist[self.p_running.current_task]
                if task[0] == 'fork':
                    self.fork()
                    # 计时，进ready
                    self.timeout()
                    # 继续下一task，若当前进程task全部完成，则重新调度
                    self.keep_next_task(self.p_running.pid)
                    continue
                elif task[0] == 'access':
                    self.memory_manager.access_memory(self.p_running.pid, task[1])
                    print(f'[pid {self.p_running.pid}] process accessed [memory {task[1]}] successfully.')
                    self.timeout()
                    self.keep_next_task(self.p_running.pid)
                    continue        
                elif task[0] == 'printer':
                    self.io_wait()
                    # TODO 加入队列后下一条
                    continue
                elif task[0] == 'cpu':
                    if task[1] > self.time_slot:
                        self.timeout()
                        task[1] -= self.time_slot
                        continue
                    else:
                        time.sleep(task[1])
                        print(f'[pid {self.p_running.pid}] process activaly released cpu.')
                        if self.keep_next_task(self.p_running.pid) == True:
                            self.p_running.status = 'ready'
                            level = self.p_running.priority
                            self.ready_queue[level].append(self.p_running.pid)
                            continue        
            

    def error_handler(self, type, pid=-1):
        if type == 'mem':
            print("Failed to create new process: No enough memory.")
        elif type == 'exec':
            print('Failed to exucute: Not an executable file.')
        elif type == 'kill_nopid':
            print(f'kill: kill [pid #{pid}] failed: no such process')
        elif type == 'kill_already':
            print(f'kill: kill [pid #{pid}] failed: the process is already terminiated')


if __name__ == '__main__':
    memory = MemoryManager(mode=memory_management_mode,page_size=memory_page_size,
                                                page_number=memory_page_number,
                                                physical_page=memory_physical_page_number)
    pm = ProcessManager(memory)
    # 三个线程负责输入、后台逻辑、io设备运行
    input_thread = threading.Thread(target=pm.input_handler)
    logical_thread = threading.Thread(target=pm.start_manager)
    IOdevice_thread = threading.Thread(target=pm.io_device_handler)

    input_thread.start()
    logical_thread.setDaemon(True)
    IOdevice_thread.setDaemon(True)
    logical_thread.start()
    IOdevice_thread.start()