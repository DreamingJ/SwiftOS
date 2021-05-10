# coding=utf-8

import signal
from colorama import init
from time import sleep
from shell import Shell
from file_manager import FileManager
from memory_manager import MemoryManager
from process_manager import ProcessManager
import const
import os
import threading

class Kernel:
    def __init__(self):

        self.my_shell = Shell()
        self.my_filemanager = FileManager(storage_block_size, storage_track_num, storage_sec_num)
        self.my_memorymanager = MemoryManager(mode=memory_management_mode,
                                               page_size=memory_page_size,
                                               page_number=memory_page_number,
                                               frame_size=memory_frame_size,
                                               physical_page=memory_physical_page_number)
        self.my_processmanager = ProcessManager(self.my_memorymanager,time_slot, priority)

        self.my_processmanager_run = threading.Thread(target=self.my_processmanager.run)
        self.my_processmanager_run.start()
    


    def help_command(self,cmdList):
        command_info = {
            'man': 'manual page, format: man [command1] [command2] ...',
            'sudo': 'enter administrator mode,then you need input name and password,format:sudo',
            'ls': 'list directory contents, format: ls [-a|-l|-al] [path]',
            'cd': 'change current working directory, format: cd [path]',
            'rm': 'remove file or directory recursively, format: rm [-r|-f|-rf] path',
            'mkdir': 'create directory, format: mkdir [path]',
            'mkf': 'create common file, format: mkf path type size',
            'dss': 'display storage status, format: dss',
            'dms': 'display memory status, format: dms',
            'exec': 'execute file, format: exec path',
            'chmod': 'change mode of file, format: chmod path new_mode',
            'ps': 'display process status, format: ps',
            'rs': 'display resource status, format: rs',
            #'mon': 'start monitoring system resources, format: mon [-o], use -o to stop',
            'td': 'tidy and defragment your disk, format: td',
            'kill': 'kill process, format: kill [pid]',
            'exit': 'exit SwiftOS'
        }
        if len(cmdList) == 0:
            cmdList = command_info.keys()
            print('请输入你想查找的命令'+cmdList)
        for cmd in cmdList:
            if cmd in command_info.keys():
                print(cmd,'--',command_info[cmd])
            else:
                print('error!!'+cmd+'no such command')


    def run(self):
        userStatus = 0
        while True:
            command_list = self.my_shell.get_command(cwd=self.my_filemanager.current_path)
            if len(command_list) == 0:
                continue
            for commands in command_list:
                if len(commands) == 0:
                    continue

                order = commands[0] #命令头名字
                argc = len(commands)

                if tool == 'man':
                    self.help_command(cmd_list=commands[1:])

                elif tool =='sudo':
                    print('username: ')
                    input(name)
                    #if name in 

                elif tool == 'ls':
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
                            self.my_file_manager.ls(dir_path=path, mode=mode)
                    else:
                        self.my_file_manager.ls()

                elif tool == 'cd':
                    if argc >= 2:
                        self.my_file_manager.cd(dir_path=commands[1])
                    else:#目录不变
                        self.my_file_manager.cd(dir_path=os.sep)

                elif tool == 'rm':
                    if argc >= 2:
                        if command_split[1][0] == '-':
                            mode = command_split[1]
                            path_list = command_split[2:]
                            if len(path_list) == 0:
                                self.report_error(cmd=tool)
                        else:
                            mode = ''
                            path_list = command_split[1:]
                        for path in path_list:
                            self.my_file_manager.rm(file_path=path, mode=mode)
                    else:
                        self.report_error(cmd=tool)

                elif tool == 'mkf':
                    #lsy 新增逻辑 实现mkf可变参数 content可以省略问题
                    if argc == 5:
                        self.my_file_manager.mkf(
                            file_path=command_split[1],
                            file_type=command_split[2],
                            size=command_split[3],
                            # 新增 lsy
                            content=command_split[4])
                    elif argc == 4:
                        self.my_file_manager.mkf(
                            file_path=command_split[1],
                            file_type=command_split[2],
                            size=command_split[3])
                    else:
                        self.report_error(cmd=tool)

                elif tool == 'mkdir':
                    if argc >= 2:
                        for path in command_split[1:]:
                            self.my_file_manager.mkdir(dir_path=path)
                    else:
                        self.report_error(cmd=tool)

                elif tool == 'dss':
                    self.my_file_manager.showBlockStatus()

                elif tool == 'dms':
                    self.my_memory_manager.display_memory_status()
                    # self.my_shell.block(func=self.my_memory_manager.display_memory_status)

                elif tool == 'exec':
                    if argc >= 2:
                        path_list = command_split[1:]
                        for path in path_list:
                            my_file = self.my_file_manager.getFileCatchE(
                                file_path=path, seek_algo=seek_algo)
                            if my_file:
                                if my_file['type'][3] == 'x':
                                    self.my_process_manager.create_process(
                                        file=my_file)
                                else:
                                    self.report_error(
                                        cmd=tool, err_msg='no execution permission')
                            else:
                                self.report_error(cmd=tool)
                    else:
                        self.report_error(cmd=tool)


                elif tool == 'ps':
                    self.my_process_manager.print_process_status()
                    
               
                elif tool == 'kill':
                    if argc >= 2:
                        for pid in command_split[1:]:
                            pid_to_kill = int(pid)
                            kill_res = self.my_process_manager.kill_process(
                                pid=pid_to_kill)
                            if kill_res:
                                self.my_memory_manager.free(pid=pid_to_kill)
                    else:
                        self.report_error(cmd=tool)

                elif tool == 'exit':
                    self.my_process_manager.running = False
                    exit(0)

                else:
                    print('ERROR!!no such command!')




if __name__ == '__main__':
    init(autoreset=True)
    my_kernel = Kernel()
    my_kernel.run()