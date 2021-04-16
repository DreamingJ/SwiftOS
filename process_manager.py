#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import copy
import threading

""" 几个可能问题：
TODO
        mem_manager没被import就直接用吗？
        .pc的逻辑可以被优化吗？
        timeout函数逻辑放哪里
"""


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
                info[1] = int(info[1])
            self.tasklist.append(info)  # example: [[printer, 18], [cpu, 170]]
        self.current_task = -1


class ProcessManager(object):
    """ Provide functions to manage process"""
    def __init__(self, memory_manager, time_slot=1, priority=True):
        """ 
        Args:
            pid_no: 下个进程的序号
            pcblist: 被管理进程的PCB
            ready_quene: 就绪队列，分为三个优先级
            waiting_quene:等待队列
            p_running：正在运行的进程，引用pcb，同一时间只有一个
            memory_manager: 每个进程所对应的内存及其管理器
            mem_of_pid：每个进程所对应的内存号
        """
        self.pid_no = 0
        self.pcblist = []
        self.ready_quene = [[] for i in range(3)]
        self.waiting_quene = []
        self.p_running = None
        self.memory_manager=memory_manager
        self.time_slot=time_slot
        self.priority=priority
        self.mem_of_pid = {}

    def create(self, exefile):
        """ 打开程序文件创建进程 """
        if exefile['type'] != 'exec':
            self.error_handler('exec')
        else:
            mem_no = self.memory_manager.alloc(self.pid_no, int(exefile['size'])) 
            if mem_no == -1:
                self.error_handler('mem')
            else:
                pcb = PCB(self.pid_no, exefile['name'], exefile['priority'], exefile['content'], int(exefile['size']))
                self.pcblist.append(pcb)
                self.ready_quene[exefile['priority']].append(pcb.pid)
                self.mem_of_pid[pcb.pid] = mem_no
                self.pid_no += 1
                print(f'[pid {pcb.pid}] process created successfully')

    def fork(self):
        """ 创建子进程 """
        child_msize = self.p_running.msize
        mem_no = self.memory_manager.alloc(self.pid_no, child_msize) 
        if mem_no == -1:
            self.error_handler('mem')
        else:
            # 初始化子进程pcb
            child_pcb = copy.deepcopy(self.p_running) 
            child_pcb.pid = self.pid_no
            child_pcb.parent_id = self.p_running.pid
            child_pcb.create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

            self.pcblist.append(child_pcb)
            self.ready_quene[child_pcb.priority].append(child_pcb.pid)
            self.pid_no += 1
            self.p_running.child_pid_list
            print(f'[pid {self.pid_no}] process forked successfully by [pid {self.p_running.pid}]' )



    def get_status(self, pid):
        """ 获取进程当前状态 """
        return self.pcblist[pid].status

    def dispatch(self):
        """ 调度进程，ready->running """
        for level in range(0, len(self.ready_quene)):
            if self.ready_quene[level]:
                self.p_running = self.pcblist(self.ready_quene[level][0])
                self.ready_quene[level].pop(0)
                self.p_running.status = 'running'
        self.p_running = None  # ready队列为空，无进程正在运行

    def timeout(self):
        """ 时间片用尽，running->ready/terminate """
        if self.p_running:
            # 当前是否执行到进程的最后一条任务
            if self.p_running.current_task == len(self.p_running.command_quene):
                terminate()
            # 进程进入就绪队列继续等待执行
            else:
                self.p_running.status = 'ready'
                level = self.p_running.priority
                self.ready_quene[level].append(self.p_running.pid)
        self.dispatch()

    def io_wait(self, pid):
        """ 等待io事件，running->waiting """
        pass
    
    def io_completion(self, pid):
        """ io完成，wating->ready """
        pass

    def kill_process(self, pid):
        pass

    def start_manager(self):
        """ 主逻辑，启动模块并运行 """

    def error_handler(self, type):
        if type == 'mem':
            print("Failed to create new process: No enough memory.")
        elif type== 'exec':
            print('Failed to exucute: Not an executable file.')
        elif type == 'kill':
            print('Failed to kill process: No such process.')


if __name__ == '__main__':
    pm = ProcessManager()
