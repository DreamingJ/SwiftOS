# coding=utf-8
import json
import os
import copy
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


class Block:
    def __init__(self, total_space, loc):
        self.total_space = total_space
        self.free_space = total_space
        self.fp = None
        self.loc = loc

    def set_free_space(self, fs):
        self.free_space = fs

    def get_free_space(self):
        return self.free_space

    def set_fp(self, fp):
        self.fp = fp

    def get_fp(self):
        return self.fp

    def get_loc(self):
        return self.loc


class FileManager:
    file_separator = os.sep
    root_path = os.getcwd() + file_separator + 'SwiftOS_files'  # Win下为\, linux下需要修改!

    def __init__(self, block_size=512, tracks=200, secs=12):  # block_size的单位:Byte
        # 当前工作目录相对路径, 可以与root_path一起构成绝对路径
        self.current_working_path = self.file_separator

        self.block_size = block_size
        self.block_number = tracks * secs
        self.tracks = tracks
        self.secs = secs

        self.unfillable_block = [3, 6, 9, 17]
        self.block_dir = {}
        self.bitmap = []
        self.all_blocks = self._init_blocks()

        self.set_unfillable_block()
        self.file_system_tree = self._init_file_system_tree(self.root_path)
        self.free_unfillable_block()

        self.disk = Disk(block_size, tracks, secs)

    # return file, if failed, report error and return None.
    # file_path支持绝对路径, mode格式与函数open()约定的相同

    # 展示函数, 调用时无任何文件打开, 但会模拟访存, 用预设的文件块
    # 能明显体现出各寻道算法的优劣.
    def get_file_demo(self, seek_algo='FCFS'):
        seek_queue = [(98, 3), (183, 5), (37, 2), (122, 11), (119, 5), (14, 0),
                      (124, 8), (65, 5), (67, 1), (198, 5), (105, 5), (53, 3)]
        if seek_algo == 'FCFS':
            self.disk.FCFS(seek_queue)
        elif seek_algo == 'SSTF':
            self.disk.SSTF(seek_queue)
        elif seek_algo == 'SCAN':
            self.disk.SCAN(seek_queue)
        elif seek_algo == 'C_SCAN':
            self.disk.C_SCAN(seek_queue)
        elif seek_algo == 'LOOK':
            self.disk.LOOK(seek_queue)
        elif seek_algo == 'C_LOOK':
            self.disk.C_LOOK(seek_queue)
        else:
            print(
                "get_file: cannot get file. '" +
                seek_algo +
                "' no such disk seek algorithm")

    def get_file(self, file_path, mode='r', seek_algo='FCFS'):
        # 由于open()能完成绝大多数工作, 该函数的主要功能体现在排除异常:
        (upper_path, basename) = self.path_split(file_path)
        current_working_dict = self.path2dict(upper_path)
        # 异常1.当路径文件夹不存在时, 报错,报错在 path2dict() 中进行
        if current_working_dict == -1:
            pass
        else:
            # 异常2.文件不存在
            if basename in current_working_dict:
                # 异常3.是文件夹
                if not isinstance(current_working_dict[basename], dict):
                    # 相对路径
                    if file_path[0] != self.file_separator:
                        gf_path = self.root_path + self.current_working_path + file_path
                    # 绝对路径
                    else:
                        gf_path = self.root_path + file_path

                    seek_queue = self.fp2loc(file_path)
                    if seek_algo == 'FCFS':
                        self.disk.FCFS(seek_queue)
                    elif seek_algo == 'SSTF':
                        self.disk.SSTF(seek_queue)
                    elif seek_algo == 'SCAN':
                        self.disk.SCAN(seek_queue)
                    elif seek_algo == 'C_SCAN':
                        self.disk.C_SCAN(seek_queue)
                    elif seek_algo == 'LOOK':
                        self.disk.LOOK(seek_queue)
                    elif seek_algo == 'C_LOOK':
                        self.disk.C_LOOK(seek_queue)
                    else:
                        print("get_file: cannot get file '" + basename +
                              "': '" + seek_algo + "' no such disk seek algorithm")
                    # 未解决异常! 直接把形参mode丢到open()了.
                    f = open(gf_path, mode)
                    # print("get_file success")
                    return json.load(f)
                else:
                    print(
                        "get_file: cannot get file'" +
                        basename +
                        "': dir not a common file")
            else:
                print(
                    "get_file: cannot get file'" +
                    basename +
                    "': file not exist")

        return False

    # 递归地构建文件树
    def _init_file_system_tree(self, now_path):  # now_path是当前递归到的绝对路径
        ''' 文件树采用字典形式, 文件名为键,
            当该文件为文件夹时, 其值为一个字典
            否则, 其值为长度为4的字符串, 表示类型 / 读 / 写 / 执行. '''
        file_list = os.listdir(now_path)
        part_of_tree = {}  # 当前文件夹对应的字典
        for file in file_list:
            file_path = os.path.join(now_path, file)
            if os.path.isdir(file_path):  # 文件夹为键 其值为字典
                part_of_tree[file] = self._init_file_system_tree(file_path)
            else:
                with open(file_path) as f:  # 普通文件为键, 其值为该文件的属性
                    # print(file_path)
                    data = json.load(f)
                    part_of_tree[file] = data['type']
                    if self.fill_file_into_blocks(
                            data, file_path[len(self.root_path):]) == -1:  # 将此文件的信息存于外存块中
                        # 没有足够的存储空间
                        print("block storage error: No Enough Initial Space")
        return part_of_tree

    def cal_loc(self, block_num):  # 计算每个文件块所绑定的位置
        track = int(block_num / self.secs)
        sec = block_num % self.secs
        return track, sec

    def fp2loc(self, fp):  # 输入fp，得到其位置list
        # 当fp为相对路径时, 转成绝对路径
        if fp[0] != self.file_separator:
            fp = self.current_working_path + fp
        start, length, size = self.block_dir[fp]
        loc_list = []
        for i in range(start, start + length):
            loc_list.append(self.all_blocks[i].get_loc())
        return loc_list

    def bitmap2str(self, bm):  # 将ndarray类型的bitmap转换为string
        return "".join([str(int(x)) for x in list(bm)])

    def _init_blocks(self):  # 初始化文件块
        blocks = []  # 块序列
        for i in range(self.block_number):  # 新分配blocks
            b = Block(self.block_size, self.cal_loc(i))
            blocks.append(b)
        self.bitmap = np.ones(self.block_number)  # 初始化bitmap
        return blocks

    def block_first_fit(self, goal_str):  # first fit文件填充算法，goal_str指需要的连续块（bitmap形式）的字串
        bitmap_str = self.bitmap2str(self.bitmap)
        first_free_block = bitmap_str.find(goal_str)
        return first_free_block

    def block_best_fit(self, goal_str):  # best fit文件填充算法
        count = 0
        free_blocks = []
        for i in range(len(self.bitmap)):  # 先遍历出所有free的blocks
            bit = self.bitmap[i]
            if bit == 0:
                count = 0
                continue
            else:
                if count == 0:
                    free_blocks.append([i, 0])
                count += 1
                free_blocks[-1][1] = count
        free_blocks = sorted(free_blocks, key=lambda k: k[1], reverse=False)
        for i in free_blocks:
            if i[1] >= len(goal_str):
                return i[0]

    def block_worst_fit(self, goal_str):  # worst fit文件填充算法
        count = 0
        free_blocks = []
        for i in range(len(self.bitmap)):  # 先遍历出所有free的blocks
            bit = self.bitmap[i]
            if bit == 0:
                count = 0
                continue
            else:
                if count == 0:
                    free_blocks.append([i, 0])
                count += 1
                free_blocks[-1][1] = count
        free_blocks = sorted(free_blocks, key=lambda k: k[1], reverse=True)
        return free_blocks[0][0]

    # num:需要的blocks数，此函数用于寻找连续的num个free blocks
    def find_free_blocks(self, num, method=0):
        goal_str = self.bitmap2str(np.ones(num))
        if method == 0:
            return self.block_first_fit(goal_str)
        elif method == 1:
            return self.block_best_fit(goal_str)
        elif method == 2:
            return self.block_worst_fit(goal_str)
        else:
            print("error: please set a legal free blocks finding method.")
            return -1

    def fill_file_into_blocks(self, f, fp, method=0):  # 将此文件的信息存于外存块中
        num = int(int(f["size"]) / self.block_size)
        occupy = int(f["size"]) % self.block_size
        first_free_block = self.find_free_blocks(num + 1, method)
        if first_free_block == -1:  # 没有足够空间存储此文件
            return -1
        free = self.block_size - occupy
        self.block_dir[fp] = (first_free_block, num + 1,
                              int(f["size"]))  # block分配信息存在dir中
        count = int(first_free_block)
        for i in range(num + 1):
            if i == num:  # 最后一块可能有碎片
                self.all_blocks[count].set_free_space(free)
            else:
                self.all_blocks[count].set_free_space(0)
            self.bitmap[count] = 0
            self.all_blocks[count].set_fp(fp)
            count += 1
        return 0

    def delete_file_from_blocks(self, fp):  # 在文件块中删除文件
        start = self.block_dir[fp][0]
        length = self.block_dir[fp][1]
        for i in range(start, start + length):
            self.all_blocks[i].set_free_space(self.block_size)
            self.all_blocks[i].set_fp(None)
            self.bitmap[i] = 1
        del self.block_dir[fp]
        return

    def tidy_disk(self):  # 整理磁盘碎片
        block_dir = copy.deepcopy(self.block_dir)
        self.all_blocks = self._init_blocks()
        for f in block_dir.items():
            self.fill_file_into_blocks({"size": f[1][2]}, f[0])
        print('tidy disk complete')

    def set_unfillable_block(self):
        for i in self.unfillable_block:
            self.bitmap[i] = 0

    def free_unfillable_block(self):
        for i in self.unfillable_block:
            self.bitmap[i] = 1

    # 将 "目录的相对或绝对路径" 转化为 当前目录的字典, 用于之后的判断 文件存在 / 文件类型 几乎所有函数的第一句都是它
    def path2dict(self, dir_path):
        if dir_path == '' or dir_path[0] != self.file_separator:
            dir_path = self.current_working_path + dir_path

        dir_list = dir_path.split(self.file_separator)
        dir_list = [i for i in dir_list if i != '']  # 去除由\分割出的空值
        dir_dict = self.file_system_tree
        try:
            upper_dir_dict_stack = []
            upper_dir_dict_stack.append(dir_dict)
            for i in range(len(dir_list)):
                if dir_list[i] == ".":
                    pass
                elif dir_list[i] == '..':
                    if upper_dir_dict_stack:
                        dir_dict = upper_dir_dict_stack.pop()
                    else:
                        dir_dict = self.file_system_tree
                else:
                    upper_dir_dict_stack.append(dir_dict)
                    dir_dict = dir_dict[dir_list[i]]
            if not isinstance(dir_dict, dict):
                pass

            return dir_dict
        # 出错, 即认为路径与当前文件树不匹配, 后续函数会用它来判断"文件夹"是否存在
        except KeyError:
            print("path error")
            return -1  # 返回错误值, 便于外层函数判断路径错误

    # 将 "路径" 分割为 该文件所在的目录 和 该文件名, 以元组返回
    def path_split(self, path):
        # 无视输入时末尾的\,但"\"(根目录)除外
        if len(path) != 1:
            path = path.rstrip(self.file_separator)
        # 从最后一个\分割开, 前一部分为该文件所在的目录(末尾有\), 后一部分为该文件
        basename = path.split(self.file_separator)[-1]
        upper_path = path[:len(path) - (len(basename))]
        # 除去"前一部分"末尾的\, 但"\"(根目录)除外
        if len(upper_path) != 1:
            upper_path = upper_path.rstrip(self.file_separator)
        return (upper_path, basename)

    # command: ls
    # 2020.6.9 陈斌：添加method参数，当其为print，则代表原方法，否则为get，返回file_list
    # method == 'get' 用于实现shell的正则表达式匹配功能
    # dir_path为空时,列出当前目录文件; 非空(填相对路径时), 列出目标目录里的文件
    def ls(self, dir_path='', mode='', method='print'):
        current_working_dict = self.path2dict(dir_path)
        # 异常1:ls路径出错. 由于path2dict()中已经报错 | 注: 此处偷懒 如果目标存在, 但不是文件夹, 同样报path
        # error
        if current_working_dict == -1:
            pass
        # ls的对象是一个文件，则只显示该文件的信息
        elif not isinstance(current_working_dict, dict):
            (upper_path, basename) = self.path_split(dir_path)
            if current_working_dict[3] == 'x':
                if mode == '-l' or mode == '-al':
                    print(
                        current_working_dict,
                        '\t',
                        '\033[1;32m' +
                        basename +
                        '\033[0m')
                else:
                    # print('\033[1;32m' + basename + '\033[0m', '\t', end='')
                    print('\033[1;32m' + basename + '\033[0m')
            else:
                if mode == '-l' or mode == '-al':
                    print(current_working_dict, '\t', basename)
                else:
                    print(basename)
        # ls的对象是一个文件夹，则显示文件夹内部的信息
        else:
            file_list = current_working_dict.keys()

            if method == 'get':  # 2020.6.9 陈斌
                return file_list

            # 目录为空时, 直接结束
            if len(file_list) == 0:
                return
            if mode not in ('-a', '-l', '-al', ''):
                print(
                    "ls: invalid option'" +
                    mode +
                    "', try '-a' / '-l' / '-al'")
                return
            for file in file_list:
                # 隐藏文件不显示
                if file[0] == '.' and not mode[0:2] == '-a':
                    pass
                # 文件夹高亮蓝色显示
                elif isinstance(current_working_dict[file], dict):
                    if mode == '-l' or mode == '-al':
                        print('d---', '\t', '\033[1;34m' + file + '\033[0m')
                    else:
                        print('\033[1;34m' + file + '\033[0m', '\t', end='')
                # 可执行文件高亮绿色显示
                elif current_working_dict[file][0] == 'e':
                    if mode == '-l' or mode == '-al':
                        print(
                            current_working_dict[file],
                            '\t',
                            '\033[1;32m' +
                            file +
                            '\033[0m')
                    else:
                        print('\033[1;32m' + file + '\033[0m', '\t', end='')
                else:
                    if mode == '-l' or mode == '-al':
                        print(current_working_dict[file], '\t', file)
                    else:
                        print(file, '\t', end='')
            print('')

    # command: cd
    def cd(self, dir_path=''):  # 参数仅支持目录名, 支持相对或绝对路径 之后以path结尾的表示支持相对或绝对路径, 以name结尾的表示仅支持名
        (upper_path, basename) = self.path_split(dir_path)
        current_working_dict = self.path2dict(upper_path)
        # 异常1:cd路径出错.
        if current_working_dict == -1:
            pass
        else:
            # 空参数和'.'指向自身, 无变化
            if dir_path == '' or dir_path == '.':
                pass
            # '..'指向上一级
            elif dir_path == '..':
                self.current_working_path = self.current_working_path.rsplit(self.file_separator, 2)[
                    0] + self.file_separator
            # 参数为"\"(根目录), 由于根目录无上级目录, 无法完成下一个分支中的操作, 故在这个分支中单独操作.
            elif dir_path == os.sep:
                self.current_working_path = os.sep
            else:
                try:
                    if basename == "." or basename == ".." or isinstance(
                            current_working_dict[basename], dict):
                        # 相对路径
                        if dir_path[0] != self.file_separator:
                            # 警告! 未解决异常: 当路径以数个\结尾时, \不会被无视.
                            path_with_point = self.current_working_path + dir_path + self.file_separator
                        # 绝对路径
                        else:
                            path_with_point = dir_path + self.file_separator
                        # 消除..和.
                        dir_list = path_with_point.split(self.file_separator)
                        dir_list = [
                            i for i in dir_list if i != '']  # 去除由\分割出的空值
                        ptr = 0  # dir_list指针
                        while ptr < len(dir_list):
                            # .即自身
                            if dir_list[ptr] == '.':
                                dir_list.pop(ptr)
                            # ..表示返回上级
                            elif dir_list[ptr] == '..':
                                if ptr > 0:
                                    dir_list.pop(ptr)
                                    dir_list.pop(ptr - 1)
                                    ptr = ptr - 1
                                # 当已经到根目录时
                                else:
                                    dir_list.pop(ptr)
                            else:
                                ptr = ptr + 1
                        # 组合current_working_path
                        self.current_working_path = '\\'
                        for i in dir_list:
                            self.current_working_path += i + '\\'
                    # 异常1 文件存在但不是目录
                    else:
                        print('cd: error ' + basename + ': Not a dir')
                # 异常2 文件不存在
                except BaseException:
                    print('cd: error ' + basename + ': No such dir')

    # command: make dir
    def mkdir(self, dir_path):
        (upper_path, basename) = self.path_split(dir_path)
        current_working_dict = self.path2dict(
            upper_path)  # 将获取到的字典直接赋值, 对其修改可以影响到文件树
        # 异常1 路径出错
        if current_working_dict == -1:
            pass
        else:
            # 异常2 文件已存在
            if basename in current_working_dict:
                print("mkdir: cannot create directory '" +
                      basename +
                      "': File exists")
            else:
                # 相对路径
                if dir_path[0] != self.file_separator:
                    mkdir_path = self.root_path + self.current_working_path + dir_path
                # 绝对路径
                else:
                    mkdir_path = self.root_path + dir_path
                os.makedirs(mkdir_path)
                current_working_dict[basename] = {}
                print("mkdir success")

    # command: make file
    def mkf(self, file_path, file_type='crwx', size='233', content=None):
        if file_type[0] != 'c':
            print(
                "mkf: cannot create file'" +
                file_path +
                "': only common file can be created")
            return
        (upper_path, basename) = self.path_split(file_path)
        current_working_dict = self.path2dict(upper_path)
        json_text = {
            'name': file_path,
            'type': file_type,
            'size': size,
            'content': [content]}
        json_data = json.dumps(json_text, indent=4)
        # 异常1 路径出错
        if current_working_dict == -1:
            pass
        else:
            # 文件名是否已存在
            if basename not in current_working_dict:
                # 相对路径 先不与self.root_path相拼接, 为了紧接着的fill_file_into_blocks传参
                if file_path[0] != self.file_separator:
                    mkf_path = self.current_working_path + file_path
                # 绝对路径
                else:
                    mkf_path = file_path
                if self.fill_file_into_blocks(
                        json_text, mkf_path, method=2) == -1:  # 测试是否能装入block
                    print(
                        "mkf: cannot create file'" +
                        basename +
                        "': No enough Space")
                    return
                mkf_path = self.root_path + mkf_path
                f = open(mkf_path, 'w')
                f.write(json_data)
                f.close()
                # 同时修改文件树
                current_working_dict[basename] = file_type
                print("mkf success")
            # 异常2 文件已存在
            else:
                print("mkf: cannot create file'" + basename + "': file exists")

    # command: rm name
    def rm(self, file_path, mode=''):
        (upper_path, basename) = self.path_split(file_path)
        current_working_dict = self.path2dict(upper_path)
        # 异常 路径出错
        if current_working_dict == -1:
            pass
        else:
            # -r 与 -rf 删文件夹
            if mode[0:2] == '-r':
                try:
                    # 异常1: 目录不存在
                    if basename in current_working_dict:
                        # 相对路径
                        if file_path[0] != self.file_separator:
                            rmdir_path = self.root_path + self.current_working_path + file_path
                        # 绝对路径
                        else:
                            rmdir_path = self.root_path + file_path
                        # -rf: 递归地强制删除文件夹
                        if len(mode) == 3 and mode[2] == 'f':
                            sub_dir_dict = self.path2dict(file_path)
                            for i in copy.deepcopy(
                                    copy.deepcopy(list(sub_dir_dict.keys()))):  # 删除此目录下的每个文件
                                sub_file_path = file_path + '\\' + i
                                real_sub_file_path = rmdir_path + '\\' + i
                                # 非空的目录, 需要递归删除
                                # print(sub_dir_dict[i])
                                # print(type(sub_dir_dict[i]))
                                # print(isinstance(sub_dir_dict[i], str))
                                if isinstance(
                                        sub_dir_dict[i], dict) and sub_dir_dict[i]:
                                    self.rm(sub_file_path, '-rf')
                                # 空目录, 直接删除
                                elif isinstance(sub_dir_dict[i], dict) and not sub_dir_dict[i]:
                                    os.rmdir(real_sub_file_path)
                                # 是文件, 强制删除
                                elif isinstance(sub_dir_dict[i], str):
                                    self.rm(sub_file_path, '-f')

                            os.rmdir(rmdir_path)
                            current_working_dict.pop(basename)

                        # -r: 仅删除空文件夹
                        else:
                            # 同时修改文件树
                            os.rmdir(rmdir_path)
                            current_working_dict.pop(basename)

                    else:
                        print(
                            "rm -r: cannot remove '" +
                            basename +
                            "': No such directory")
                # 异常2 不是文件夹
                except NotADirectoryError:
                    print("rm -r: cannot remove '" + basename + "': not a dir")
                # 异常3 文件夹非空
                except OSError:
                    print(
                        "rm -r: cannot remove '" +
                        basename +
                        "': this directory is not empty, try to use 'rm -rf [path]'")
            # 空参数 或 -f 删文件
            elif mode == '' or mode == '-f':
                try:
                    if basename in current_working_dict:
                        # 相对路径
                        if file_path[0] != self.file_separator:
                            rm_path = self.current_working_path + file_path
                        # 绝对路径
                        else:
                            rm_path = file_path
                        if current_working_dict[basename][2] == 'w' or mode == '-f':
                            # 在block中删除文件
                            self.delete_file_from_blocks(rm_path)
                            rm_path = self.root_path + rm_path
                            # 删真正文件
                            os.remove(rm_path)
                            # 同时修改文件树
                            current_working_dict.pop(basename)
                        # 异常1 文件只读, 不可删除
                        else:
                            print(
                                "rm: cannot remove '" +
                                basename +
                                "': file read only, try to use -f option")
                    # 异常2 文件不存在
                    else:
                        print(
                            "rm: cannot remove '" +
                            basename +
                            "': No such file")
                # 异常3 文件是目录
                except (PermissionError, KeyError):
                    print("rm: cannot remove '" + basename +
                          "': Is a dir. Try to use -r option")
            else:
                print(
                    "rm: invalid option'" +
                    mode +
                    "', try '-r' / '-f' / '-rf'")

    # 更改文件属性, name为所该文件名称, type为四字字符(警告!此处未对此四字符进行错误检测)
    def chmod(self, file_path, file_type):
        (upper_path, basename) = self.path_split(file_path)
        current_working_dict = self.path2dict(upper_path)
        # 异常 路径出错
        if current_working_dict == -1:
            pass
        else:
            if basename in current_working_dict:
                if not isinstance(current_working_dict[basename], dict):
                    if file_path[0] != self.file_separator:
                        chmod_path = self.root_path + self.current_working_path + file_path
                    # 绝对路径
                    else:
                        chmod_path = self.root_path + file_path
                    f_in = open(chmod_path, 'r')
                    json_data = json.load(f_in)
                    json_data["type"] = file_type
                    f_out = open(chmod_path, 'w')
                    f_out.write(json.dumps(json_data, indent=4))
                    f_in.close()
                    f_out.close()
                    current_working_dict[basename] = file_type
                    print("chmod success")
                # 异常1 文件是目录
                else:
                    print(
                        "chmod: cannot change mode '" +
                        basename +
                        "': dir not a common file")
            # 异常2 文件不存在
            else:
                print(
                    "chmod: cannot change mode '" +
                    basename +
                    "': No such file")

    # # 输出当前工作路径,-r表示不输出, 仅返回
    # def pwd(self, mode=''):
    #     if mode == '-r':
    #         return self.current_working_path
    #     else:
    #         print(self.current_working_path)

    # 仅做调试用, 将文件树很好看地打印出来

    def tree_dir(self, dir=root_path, layer=0):
        listdir = os.listdir(dir)
        for index, file in enumerate(listdir):
            file_path = os.path.join(dir, file)
            print("|  " * (layer - 1), end="")
            if layer > 0:
                print("`--" if index == len(listdir) - 1 else "|--", end="")
            print(file)
            if os.path.isdir(file_path):
                self.tree_dir(file_path, layer + 1)

    # command: dss
    # print status of all blocks
    def display_storage_status(self):
        total = self.block_size * self.block_number  # 总字节数
        all_free = len(np.nonzero(self.bitmap)[0])
        all_free *= self.block_size  # 剩余的总字节数
        all_occupy = total - all_free  # 已占用的总字节数
        print(
            "total: {0} B,\t allocated: {1} B,\t free: {2} B\n".format(
                total,
                all_occupy,
                all_free))
        # for fp, item in self.block_dir.items():  # 调试用
        #     print("{:<10}: start {}\t length {}".format(fp, item[0], item[1]))
        for i in range(self.block_number):
            b = self.all_blocks[i]
            occupy = self.block_size - b.get_free_space()
            if occupy > 0:
                # all_free += b.get_free_space()
                print("block #{:<5} {:>5} / {} Byte(s)   {:<20}".format(i,
                                                                        occupy, self.block_size, str(b.get_fp())))

    # nowheadpointer 某次访存开始时磁头所在磁道号.
    def set_disk_now_headpointer(self, now_headpointer=0):
        self.disk.set_now_headpointer(now_headpointer)

    def set_disk_x_slow(self, x_slow=10):
        self.disk.set_x_slow(x_slow)

    # 画出过去所有读写磁盘操作时的平均速度柱状图
    def draw_disk_speed(self):
        self.disk.draw_disk_speed()


class Disk:
    def __init__(self, block_size, track_num, sec_num,
                 now_headpointer=53, x_slow=10):
        # 扇区大小 默认512byte
        self.sector_size = block_size
        # 每磁道中扇区数 默认12
        self.track_size = sec_num
        # 总磁道数 默认200
        self.track_num = track_num
        # 当前磁头所在磁道号
        self.now_headpointer = now_headpointer

        # 跨过一个磁道所用的时间 默认0.1ms （即平均寻道时间10ms）
        self.seek_speed = 0.0001
        # 平均寻扇区与读取的时间 默认4ms （约等于转速7200rpm）
        self.rotate_speed = 0.004
        # x_slow是减速倍数，由于time.sleep()精确到10ms级, 故默认放慢100倍
        self.x_slow = x_slow
        self.seek_speed = self.seek_speed * x_slow
        self.rotate_speed = self.rotate_speed * x_slow

        # 以下变量用于画图
        # 总读写时间(单位:S)
        self.total_time = 0
        # 总读写量(单位:B)
        self.total_byte = 0
        # 总读写速度表(单位:B/s), 在每一次用于磁盘调度执行后, 记录总平均速度
        self.total_speed_list = []
        self.speed_list = []
        self.algo_list = []

        # 2020.6.12 陈斌添加：为True则会输出图片到本地
        self.disk_monitoring = False

    # 提供两个可修改参数,
    # nowheadpointer 某次访存开始时磁头所在磁道号.
    def set_now_headpointer(self, now_headpointer=53):
        self.now_headpointer = now_headpointer

    #  x_slow为减速倍数, 让稍纵即逝的读文件过程变得缓慢, 推荐以及默认设置为10倍
    def set_x_slow(self, x_slow=10):
        # x_slow是减速倍数，由于time.sleep()精确到10ms级, 故默认放慢100倍
        self.x_slow = x_slow
        self.seek_speed = self.seek_speed * x_slow
        self.rotate_speed = self.rotate_speed * x_slow

    # 朴实无华地按照queue一个个访问磁盘
    def seek_by_queue(self, seek_queue):
        # 本次访存的耗时与读写量
        this_time_time = 0
        this_time_byte = 0
        total_track_distance = 0
        for seek_addr in seek_queue:
            # 寻道:计算磁头所要移动的距离
            track_distance = abs(seek_addr[0] - self.now_headpointer)
            total_track_distance = total_track_distance + track_distance
            # 寻道:模拟延迟并移动磁头
            time.sleep(track_distance * self.seek_speed)
            # 记录耗时(考虑减速比)
            this_time_time = this_time_time + \
                (track_distance * self.seek_speed) / self.x_slow
            # print("seek track:", seek_addr[0])
            self.now_headpointer = seek_addr[0]

            # 旋转:模拟寻扇区和读写延迟
            # 记录耗时(考虑减速比), 当扇区为-1时, 不用读写
            if seek_addr[1] == -1:
                # print("pass")
                pass
            else:
                time.sleep(self.rotate_speed)
                this_time_time = this_time_time + self.rotate_speed / self.x_slow
            # 记录读写量
            this_time_byte = this_time_byte + self.sector_size
        self.total_time = self.total_time + this_time_time
        self.total_byte = self.total_byte + this_time_byte
        print("disk access success: time used: ",
              round(this_time_time * 1000, 5), "ms")
        # print(total_track_distance)
        self.total_speed_list.append(self.total_byte / self.total_time)
        self.speed_list.append(this_time_byte / this_time_time)

    # 先来先服务
    def FCFS(self, seek_queue):
        self.seek_by_queue(seek_queue)
        self.algo_list.append('FCFS')
        if self.disk_monitoring:
            self.draw_track(seek_queue, "FCFS")

    # 最短寻道时间优先
    def SSTF(self, seek_queue):
        # 暂存经过SSTF排序后的seek_queue
        temp_seek_queue = [(self.now_headpointer, 0)]
        while seek_queue:
            min_track_distance = self.track_num
            for seek_addr in seek_queue:
                temp_now_headpointer = temp_seek_queue[-1][0]
                track_distance = abs(seek_addr[0] - temp_now_headpointer)
                if track_distance < min_track_distance:
                    min_track_distance = track_distance
                    loc = seek_queue.index(seek_addr)
            temp_seek_queue.append(seek_queue[loc])
            seek_queue.pop(loc)
        temp_seek_queue.pop(0)
        seek_queue = temp_seek_queue

        self.seek_by_queue(seek_queue)
        self.algo_list.append('SSTF')
        if self.disk_monitoring:
            self.draw_track(seek_queue, "SSTF")

    # 先正向扫描,扫到头,再负向扫描
    def SCAN(self, seek_queue):
        # 暂存经过SCAN方法排序后的seek_queue
        temp_seek_queue = []
        seek_queue.sort(key=lambda item: item[0])
        for loc in range(len(seek_queue)):
            if seek_queue[loc][0] >= self.now_headpointer:
                break
        # 比now_headpointer大的部分,正序访问
        temp_seek_queue.extend(seek_queue[loc:])
        # 走到头
        if temp_seek_queue == seek_queue:
            pass
        else:
            temp_seek_queue.append((self.track_num - 1, -1))
            # 比now_headpointer小的部分,负序访问
            temp_seek_queue.extend(seek_queue[loc - 1::-1])
            seek_queue = temp_seek_queue
        self.seek_by_queue(seek_queue)
        self.algo_list.append('SCAN')
        if self.disk_monitoring:
            self.draw_track(seek_queue, "SCAN")

    # 先正向扫描,扫到头,归0,再正向扫描
    def C_SCAN(self, seek_queue):
        # 暂存经过C_SCAN方法排序后的seek_queue
        temp_seek_queue = []
        seek_queue.sort(key=lambda item: item[0])
        for loc in range(len(seek_queue)):
            if seek_queue[loc][0] >= self.now_headpointer:
                break
        # 比now_headpointer大的部分,正序访问
        temp_seek_queue.extend(seek_queue[loc:])
        # 如果只有比now_headpointer大的部分,就不用回头了
        if temp_seek_queue == seek_queue:
            pass
        else:
            # 走到头
            temp_seek_queue.append((self.track_num - 1, -1))
            # 归零
            temp_seek_queue.append((0, -1))
            # 比now_headpointer小的部分,负序访问
            temp_seek_queue.extend(seek_queue[:loc])
            seek_queue = temp_seek_queue
        self.seek_by_queue(seek_queue)
        self.algo_list.append('C_SCAN')
        if self.disk_monitoring:
            self.draw_track(seek_queue, "C_SCAN")

    # 先正向扫描,不扫到头,再负向扫描
    def LOOK(self, seek_queue):
        # 暂存经过LOOK排序后的seek_queue
        temp_seek_queue = []
        seek_queue.sort(key=lambda item: item[0])
        for loc in range(len(seek_queue)):
            if seek_queue[loc][0] >= self.now_headpointer:
                break
        # 比now_headpointer大的部分,正序访问
        temp_seek_queue.extend(seek_queue[loc:])
        if temp_seek_queue == seek_queue:
            pass
        else:
            # 比now_headpointer小的部分,负序访问
            temp_seek_queue.extend(seek_queue[loc - 1::-1])
            seek_queue = temp_seek_queue

        self.seek_by_queue(seek_queue)
        self.algo_list.append('LOOK')
        if self.disk_monitoring:
            self.draw_track(seek_queue, "LOOK")

    # 先正向扫描,不扫到头,归0,再正向扫描
    def C_LOOK(self, seek_queue):
        # 暂存经过C_LOOK方法排序后的seek_queue
        temp_seek_queue = []
        seek_queue.sort(key=lambda item: item[0])
        for loc in range(len(seek_queue)):
            if seek_queue[loc][0] >= self.now_headpointer:
                break
        # 比now_headpointer大的部分,正序访问
        temp_seek_queue.extend(seek_queue[loc:])
        # 比now_headpointer小的部分,正序访问
        temp_seek_queue.extend(seek_queue[:loc])
        seek_queue = temp_seek_queue
        self.seek_by_queue(seek_queue)
        self.algo_list.append('C_LOOK')
        if self.disk_monitoring:
            self.draw_track(seek_queue, "C_LOOK")

    def draw_disk_speed(self):
        plt.close("all")
        # ax = plt.subplot()
        plt.xlabel('disk access_algo')
        plt.ylabel('speed: MB/s')
        index = range(len(self.speed_list))
        speed_list_MB = np.array(self.speed_list) / 1000
        # print(speed_list_MB)
        plt.bar(index, speed_list_MB, color="#87CEFA", width=0.35)
        plt.xticks(index, self.algo_list)
        plt.savefig('disk.jpg')
        # plt.show()

    def draw_track(self, seek_queue, algo):
        plt.close("all")
        track_queue = []
        for seek_addr in seek_queue:
            track_queue.append(seek_addr[0])
        ax = plt.subplot()
        # plt.xlabel('')
        plt.ylabel('track_no')
        # 隐藏右上下边
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        plt.xticks([])
        plt.plot(track_queue, marker='>', mec='r', mfc='w', color='k')
        for i in range(len(track_queue)):
            plt.text(i, track_queue[i], track_queue[i])
        plt.title(algo + " track")
        plt.savefig('last_track.jpg')


if __name__ == '__main__':
    a = FileManager()
    # a.get_file('f1')
    # a.display_storage_status()
    # 新增实际磁盘位置返回函数+指定新文件填入算法+磁盘碎片整理，更改dss的输出方式（以文件块的空满为标准计算空闲空间，而不是实际字节数）
    # a.rm("123")
    # a.mkf("123", size="10000")
    # a = FileManager()
    # a.set_disk_now_headpointer(53)
    # a.get_file('123', seek_algo = 'FCFS')
    # a.set_disk_now_headpointer(53)
    # a.get_file('123', seek_algo = 'SSTF')
    # a.set_disk_now_headpointer(53)
    # a.get_file('123', seek_algo = 'SCAN')
    # a.set_disk_now_headpointer(53)
    # a.get_file('123', seek_algo = 'C_SCAN')
    # a.set_disk_now_headpointer(53)
    # a.get_file('123', seek_algo = 'LOOK')
    # a.set_disk_now_headpointer(53)
    # a.get_file('123', seek_algo = 'C_LOOK')
    # a.draw_disk_speed()

    a.set_disk_now_headpointer(53)
    a.get_file_demo(seek_algo='FCFS')
    a.set_disk_now_headpointer(53)
    a.get_file_demo(seek_algo='SSTF')
    a.set_disk_now_headpointer(53)
    a.get_file_demo(seek_algo='SCAN')
    a.set_disk_now_headpointer(53)
    a.get_file_demo(seek_algo='C_SCAN')
    a.set_disk_now_headpointer(53)
    a.get_file_demo(seek_algo='LOOK')
    a.set_disk_now_headpointer(53)
    a.get_file_demo(seek_algo='C_LOOK')
    a.draw_disk_speed()
