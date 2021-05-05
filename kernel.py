# coding=utf-8

import signal
from colorama import init
from time import sleep
from shell import Shell
from file_manager import FileManager
from memory_manager import MemoryManager
from process_manager import ProcessManager
from config import *
import os
import threading
import matplotlib


class Kernel:
    def __init__(self):
        self.my_shell = Shell()
        self.my_file_manager = FileManager(storage_block_size,
                                           storage_track_num, storage_sec_num)
        self.my_memory_manager = MemoryManager(
            mode=memory_management_mode,
            page_size=memory_page_size,
            page_number=memory_page_number,
            physical_page=memory_physical_page_number)
        self.my_process_manager = ProcessManager(self.my_memory_manager)

        self.is_monitoring = False
        # start process manager
        self.my_process_manager_run_thread = threading.Thread(
            target=self.my_process_manager.start_manager)
        self.my_process_manager_run_thread.start()

        # printer Threading
        self.IOdevice_thread = threading.Thread(target=self.my_process_manager.io_device_handler)
        self.IOdevice_thread.start()
        
        # signal.signal(signal.SIGINT, self.my_shell.deblock)

    # monitoring all resources
    def monitoring(self, interval=1):
        self.is_monitoring = True
        self.my_file_manager.disk.disk_monitoring = True
        while self.is_monitoring:
            self.my_process_manager.resource_monitor()
            self.my_memory_manager.memory_watching()
            self.my_file_manager.draw_disk_speed()
            sleep(interval)

    def report_error(self, cmd, err_msg=''):
        print('[error %s] %s' % (cmd, err_msg))
        if err_msg == '':
            self.display_command_description(cmd_list=[cmd])

    # command: man [cmd1] [cmd2] ...
    def display_command_description(self, cmd_list):
        command_to_description = {
            'man': 'manual page, format: man [command1] [command2] ...',
            'ls': 'list directory contents, format: ls [-a|-l|-al] [path]',
            'cd': 'change current working directory, format: cd [path]',
            'rm':
            'remove file or directory recursively, format: rm [-r|-f|-rf] path',
            'mkdir': 'create directory, format: mkdir path',
            'mkf':
            'create common file, format: mkf path type size, e.g. mkf my_file crwx 300',
            'dss': 'display storage status, format: dss',
            'dms': 'display memory status, format: dms',
            'exec': 'execute file, format: exec path, e.g. exec test',
            'chmod':
            'change mode of file, format: chmod path new_mode, e.g. chmod test erwx',
            'ps': 'display process status, format: ps',
            'rs': 'display resource status, format: rs',
            'mon':
            'start monitoring system resources, format: mon [-o], use -o to stop',
            'td': 'tidy and defragment your disk, format: td',
            'kill': 'kill process, format: kill pid',
            'exit': 'exit MiniOS'
        }
        if len(cmd_list) == 0:
            cmd_list = command_to_description.keys()
        for cmd in cmd_list:
            if cmd in command_to_description.keys():
                print(cmd, '-', command_to_description[cmd])
            else:
                self.report_error(cmd=cmd, err_msg='no such command')

    def run(self):
        while True:
            # a list of commands split by space or tab
            current_file_list = self.my_file_manager.ls(method='get')
            command_split_list = self.my_shell.get_split_command(
                cwd=self.my_file_manager.current_working_path,
                file_list=current_file_list)

            # this indicates user push Enter directly, then nothing to happen
            if len(command_split_list) == 0:
                continue

            for command_split in command_split_list:
                if len(command_split) == 0:  # an empty command
                    continue

                tool = command_split[0]  # tool name, e.g. ls, cd, ...

                argc = len(command_split)  # argument count

                if tool == 'man':
                    self.display_command_description(
                        cmd_list=command_split[1:])

                elif tool == 'ls':
                    if argc >= 2:
                        if command_split[1][0] == '-':
                            mode = command_split[1]
                            path_list = command_split[2:]
                            if len(path_list) == 0:
                                path_list = ['']
                        else:
                            mode = ''
                            path_list = command_split[1:]
                        for path in path_list:
                            self.my_file_manager.ls(dir_path=path, mode=mode)
                    else:
                        self.my_file_manager.ls()

                elif tool == 'cd':
                    if argc >= 2:
                        self.my_file_manager.cd(dir_path=command_split[1])
                    else:
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

                elif tool == 'chmod':
                    if argc >= 3:
                        self.my_file_manager.chmod(file_path=command_split[1],
                                                   file_type=command_split[2])
                    else:
                        self.report_error(cmd=tool)

                elif tool == 'mkf':
                    if argc >= 4:
                        self.my_file_manager.mkf(file_path=command_split[1],
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
                    self.my_file_manager.display_storage_status()

                elif tool == 'dms':
                    self.my_memory_manager.display_memory_status()
                    # self.my_shell.block(func=self.my_memory_manager.display_memory_status)

                elif tool == 'exec':
                    if argc >= 2:
                        path_list = command_split[1:]
                        for path in path_list:
                            my_file = self.my_file_manager.get_file(
                                file_path=path, seek_algo=seek_algo)
                            if my_file:
                                if my_file['type'][3] == 'x':
                                    self.my_process_manager.create(
                                        exefile=my_file)
                                else:
                                    self.report_error(
                                        cmd=tool,
                                        err_msg='no execution permission')
                            else:
                                self.report_error(cmd=tool)
                    else:
                        self.report_error(cmd=tool)

                elif tool == 'ps':
                    self.my_process_manager.print_process_status()
                    # self.my_shell.block(func=self.my_process_manager.process_status)

                elif tool == 'rs':
                    self.my_process_manager.print_resource_status()
                    # self.my_shell.block(func=self.my_process_manager.resource_status)

                elif tool == 'mon':
                    if argc >= 2 and command_split[1] == '-o':
                        print('Stop monitoring')
                        self.is_monitoring = False
                        self.my_file_manager.disk.disk_monitoring = False
                    else:
                        # start monitoring
                        print('Start monitoring')
                        monitor_thread = threading.Thread(
                            target=self.monitoring)
                        monitor_thread.daemon = True
                        monitor_thread.start()

                elif tool == 'td':
                    self.my_file_manager.tidy_disk()

                elif tool == 'kill':
                    if argc >= 2:
                        for pid in command_split[1:]:
                            pid_to_kill = int(pid)
                            kill_res = self.my_process_manager.kill(
                                pid=pid_to_kill)
                            if kill_res:
                                self.my_memory_manager.free(pid=pid_to_kill)
                    else:
                        self.report_error(cmd=tool)

                elif tool == 'exit':
                    self.my_process_manager.is_running = False
                    exit(0)

                else:
                    self.report_error(cmd=tool, err_msg='no such command')


if __name__ == '__main__':
    init(autoreset=True)
    matplotlib.use('Agg')
    my_kernel = Kernel()
    my_kernel.run()
