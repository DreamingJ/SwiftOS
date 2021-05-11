# coding=utf-8

import signal
from colorama import init
from time import sleep
from shell import Shell
from file_manager import FileManager
from memory_manager import MemoryManager
from process_manager import ProcessManager
from config import *
from devices import Printer, Disk
import os
import sys
import threading
import logging
import datetime
#from . import config


class Kernel:
    def __init__(self,):
        self.userStatus = 0

        self.my_shell = Shell()
        self.username = sys.argv[1]
        self.my_printer = Printer()
        self.my_disk = Disk()
        self.my_filemanager = FileManager(storage_block_size,
                                          storage_track_num, storage_sec_num,
                                          seek_algo, self.username)
        self.my_memorymanager = MemoryManager(storage_mode, option, page_size,
                                              page_total, frame_size,
                                              frame_total)
        self.my_processmanager = ProcessManager(self.my_memorymanager)

        self.logical_thread_run = threading.Thread(
            target=self.my_processmanager.start_manager)
        self.IOdevice_thread_run = threading.Thread(
            target=self.my_printer.io_device_handler,
            args=(self.my_processmanager.waiting_queue, self.my_processmanager.io_completion))

        self.logical_thread_run.setDaemon(True)
        self.IOdevice_thread_run.setDaemon(True)
        self.logical_thread_run.start()
        self.IOdevice_thread_run.start()

    def help_command(self, cmdList):
        command_info = {
            'man': 'manual page, format: man [command1] [command2] ...',
            'time':'watch current date and time',
            'sudo': 'enter administrator mode,then you need input name and password,format:sudo',
            'pwd':'print current file path',
            'ls': 'list directory contents, format: ls [-a|-l|-al] [path]',
            'cd': 'change current working directory, format: cd [path]',
            'rm':
            'remove file or directory recursively, format: rm [-r|-f|-rf] path',
            'mkdir': 'create directory, format: mkdir [path]',
            'mkf': 'create common file, format: mkf path type size',
            'dss': 'display storage status, format: dss',
            'dms': 'display memory status, format: dms',
            'exec': 'execute file, format: exec path',
            'ps': 'display process status, format: ps',
            'rs': 'display resource status, format: rs',
            'td': 'tidy and defragment your disk, format: td',
            'kill': 'kill process, format: kill [pid]',
            'exit': 'exit SwiftOS cmd back to login page'
        }
        if len(cmdList) == 0:
            cmdList = command_info.keys()
            print('please input which you want to inquiry', cmdList)
        for cmd in cmdList:
            if cmd in command_info.keys():
                print(cmd, '--', command_info[cmd])
            else:
                print('error!!' + cmd + 'no such command')

    def report_error(self, cmd, err_msg=''):
        print('[error %s] %s' % (cmd, err_msg))
        if err_msg == '':
            self.help_command(cmdList=[cmd])

    def run(self):
        while True:
            # a list of commands split by space or tab
            current_file = self.my_filemanager.pathToDictionary('').keys()       
            command_list = self.my_shell.get_split_command(cwd='@'+self.username+ os.sep + self.my_filemanager.current_working_path, file_list=current_file, userStatus=self.userStatus)

            if len(command_list) == 0:
                continue
            for commands in command_list:
                if len(commands) == 0:
                    continue

                order = commands[0]  #命令头名字
                argc = len(commands)

                if order == 'man':
                    self.help_command(cmdList=commands[1:])

                elif order == 'time':
                    print("current time: ",datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                elif order == 'pwd':
                    print("current path: ",os.getcwd())

                elif order =='sudo':                    
                    pw = input('please input adminPassword: ')
                    if pw == "swiftos":  #固定的口令
                        userStatus = 1
                    else:
                        print("error adminPassword!!")

                elif order == 'ls':
                    if argc >= 2:
                        if commands[1][0] == '-':
                            mode = commands[1]
                            path_list = commands[2:]
                            if len(path_list) == 0:
                                path_list = ['']
                        else:
                            mode = ''
                            path_list = commands[1:]
                        for path in path_list:
                            self.my_filemanager.ls(dir_path=path, mode=mode)
                    else:
                        self.my_filemanager.ls()

                elif order == 'cd':
                    if argc >= 2:
                        self.my_filemanager.cd(dir_path=commands[1])
                    else:  #目录不变
                        self.my_filemanager.cd(dir_path=os.sep)

                elif order == 'rm':
                    if argc >= 2:
                        if commands[1][0] == '-':
                            mode = commands[1]
                            path_list = commands[2:]
                            if len(path_list) == 0:
                                self.report_error(cmd=order)
                        else:
                            mode = ''
                            path_list = commands[1:]
                        for path in path_list:
                            self.my_filemanager.rm(file_path=path, mode=mode)
                    else:
                        self.report_error(cmd=order)

                elif order == 'mkf':
                    #lsy 新增逻辑 实现mkf可变参数 content可以省略问题
                    if argc == 5:
                        self.my_filemanager.mkf(
                            file_path=commands[1],
                            file_type=commands[2],
                            size=commands[3],
                            # 新增 lsy
                            content=commands[4])
                    elif argc == 4:
                        self.my_filemanager.mkf(file_path=commands[1],
                                                file_type=commands[2],
                                                size=commands[3])
                    else:
                        self.report_error(cmd=order)

                elif order == 'mkdir':
                    if argc >= 2:
                        for path in commands[1:]:
                            self.my_filemanager.mkdir(dir_path=path)
                    else:
                        self.report_error(cmd=order)

                elif order == 'dss':
                    self.my_filemanager.showBlockStatus()

                elif order == 'dms':
                    self.my_memorymanager.display_memory_status()
                    # self.my_shell.block(func=self.my_memorymanager.display_memory_status)

                elif order == 'exec':
                    if argc >= 2:
                        path_list = commands[1:]
                        for path in path_list:
                            my_file = self.my_filemanager.getFileCatchE(
                                file_path=path)
                            print("******"+path)
                            if my_file:
                                if my_file['type'][3] == 'x':
                                    self.my_processmanager.create(
                                        exefile=my_file)
                                else:
                                    self.report_error(
                                        cmd=order,
                                        err_msg='no execution permission')
                            else:
                                self.report_error(cmd=order)
                    else:
                        self.report_error(cmd=order)

                elif order == 'ps':
                    self.my_processmanager.print_process_status()

                elif order == 'rs':
                    self.my_printer.print_resource_status()

                elif order == 'kill':
                    if argc >= 2:
                        for pid in commands[1:]:
                            pid_to_kill = int(pid)
                            kill_res = self.my_processmanager.kill(
                                pid=pid_to_kill)
                            if kill_res:
                                self.my_memorymanager.free(pid=pid_to_kill)
                    else:
                        self.report_error(cmd=order)

                elif order == 'exit':
                    self.my_processmanager.running = False
                    exit(0)

                else:
                    print('ERROR!!no such command!')


if __name__ == '__main__':

    _logFmt = logging.Formatter(
        '%(asctime)s %(levelname).1s %(lineno)-3d %(funcName)-20s %(message)s',
        datefmt='%H:%M:%S')
    _consoleHandler = logging.StreamHandler()
    _consoleHandler.setLevel(logging.DEBUG)
    _consoleHandler.setFormatter(_logFmt)

    log = logging.getLogger(__file__)
    log.addHandler(_consoleHandler)
    log.setLevel(logging.DEBUG)

    init(autoreset=True)
    my_kernel = Kernel()
    my_kernel.run()