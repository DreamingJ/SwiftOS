# coding=utf-8

import datetime
import os
import re
import platform
from time import sleep


class Shell:
    def __init__(self):
        self.block_flag = False
        self.clear_cmd_str = 'cls' if platform.system() == 'Windows' else 'clear'
        
        print ("****"+clear_cmd_str )
        
        self.print_system_info()

    def print_system_info(self):
        os.system(self.clear_cmd_str)
        print('SwiftOS 1.0', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # current working directory
    def get_split_command(self, cwd, file_list):
        try:
            commands = input(cwd + '$ ').split(';')
        except BaseException:
            commands = []
        for i in range(len(commands)):
            raw_command = commands[i].split()
            if len(raw_command) == 0:
                continue
            re_flag = False
            cur_cmd = raw_command[0]
            if cur_cmd == 're':
                re_flag = True
                raw_command = raw_command[1:]
            commands[i] = [raw_command[0]]
            for arg in raw_command[1:]:
                match_flag = False
                if re_flag:
                    for file_name in file_list:
                        match_res = re.match(arg + '$', file_name)
                        if match_res:
                            match_flag = True
                            commands[i].append(match_res.group(0))
                if match_flag is False:
                    commands[i].append(arg)
        # print(commands)
        return commands
