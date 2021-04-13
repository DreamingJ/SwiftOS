#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import threading

class PCB(object):
    """ ProcessControlBlock
    Atrributes:
        pid,pname,parentid,priority,create_time,status,
        tasklist: 该进程待执行的任务
    """
    def __init__(self, pid, pname, parentid, priority, create_time, content):
        self.pid = pid
        self.pname = pname
        self.parentid = parentid
        self.priority = priority
        self.create_time = create_time
        self.status = 'ready'
        self.tasklist = []
        for task in content:
            info = str.split(task)  
            if len(info) > 1:
                info[1] = int(info[1])
            self.tasklist.append(info)  # example: [[printer, 18], [cpu, 170]]


class ProcessManager(object):
    """ Provide functions to manage process"""
    def __init__(self, memory_manager, time_slot=1, priority=True):
        """ 
        Args:
            pidum:进程数量
            pcblist: 被管理进程的PCB
            ready_quene: 就绪队列，分为三个优先级
            waiting_quene:等待队列
            p_running：正在运行的进程，同一时间只有一个
            memory_manager: 每个进程所对应的内存及其管理器
        """
        self.pidnum = 0
        self.pcblist = []
        self.ready_quene = [[]for i in range(3)]
        self.waiting_quene = []
        self.p_running = -1
        self.memory_manager=memory_manager
        self.time_slot=time_slot
        self.priority=priority

    def create(self, command):
        """ 由命令创建进程 """
        pass

    def fork(self):
        """ 创建子进程 """
        pass

    def getPstatus(self):
        """ 获取进程当前状态 """
        pass

    def dispatch(self):
        """ 调度进程，ready->running """
        pass

    def timeout(self):
        """ 时间片用尽，running->ready """
        pass

    def ioWait(self, pid):
        """ 等待io事件，running->waiting """
        pass
    
    def ioCompletion(self, pid):
        """ io完成，wating->ready """
        pass

    def killProcess(self, pid):
        pass

    def startManager(self):
        """ 主逻辑，启动模块并运行 """

if __name__ == '__main__':
    pm = ProcessManager()
