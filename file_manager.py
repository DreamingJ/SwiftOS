# coding=utf-8
import json
import os
import copy
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from config import *

##############################################
# Disk存储区块框架：  
# 0 磁盘自身属性：
#       扇区大小
#       扇区数
#       磁道数
#       寻道时间
# 1 磁头移动功能函数：
#       获取磁头当前位置
#       移动磁头目标位置
#       磁头移动过程
# 2 寻道算法：
#       FCFS\SSTF\SCAN\C_SCAN\LOOK\C_LOOK 
##############################################
class Disk:
    # init 磁盘自身属性信息
    def __init__(self, block_size, track_num, sec_num,
                 now_headpointer=35, x_slow=10):
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

        # 总读写时间(单位:S)
        self.total_time = 0
        # 总读写量(单位:B)
        self.total_byte = 0
        # 总读写速度表(单位:B/s), 在每一次用于磁盘调度执行后, 记录总平均速度
        self.total_speed_list = []
        self.speed_list = []
        self.algo_list = []

        #为True则会输出图片到本地
        self.disk_monitoring = True

    # nowheadpointer 某次访存开始时磁头所在磁道号.
    def setNowHeadpointer(self, now_headpointer=35):
        self.now_headpointer = now_headpointer

    #  x_slow为减速倍数, 让稍纵即逝的读文件过程变得缓慢, 推荐以及默认设置为10倍
    def setX_slow(self, x_slow=10):
        # x_slow是减速倍数，由于time.sleep()精确到10ms级, 故默认放慢100倍
        self.x_slow = x_slow
        self.seek_speed = self.seek_speed * x_slow
        self.rotate_speed = self.rotate_speed * x_slow

    # 朴实无华地按照queue一个个访问磁盘
    def QueueSeek(self, seek_queue):
        # 本次访存的耗时与读写量
        this_time_time = 0
        this_time_byte = 0
        total_track_distance = 0
        for seek_addr in seek_queue:
            # 寻道:计算磁头所要移动的距离
            track_distance = abs(seek_addr[0] - self.now_headpointer) #abs取绝对值
            total_track_distance = total_track_distance + track_distance
            # 寻道:模拟延迟并移动磁头
            time.sleep(track_distance * self.seek_speed)
            # 记录耗时(考虑减速比)
            this_time_time = this_time_time + \
                (track_distance * self.seek_speed) / self.x_slow # 上行 + \ 单纯的分隔符
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
        print("Access Disk Time total: ", round(this_time_time * 1000, 5), "ms")
        # print(total_track_distance)
        self.total_speed_list.append(self.total_byte / self.total_time)
        self.speed_list.append(this_time_byte / this_time_time)

    # 先来先服务
    def FCFS(self, seek_queue):
        self.QueueSeek(seek_queue)
        self.algo_list.append('FCFS')
        if self.disk_monitoring:
            self.ShowTrack(seek_queue, "FCFS")

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

        self.QueueSeek(seek_queue)
        self.algo_list.append('SSTF')
        if self.disk_monitoring:
            self.ShowTrack(seek_queue, "SSTF")

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
        self.QueueSeek(seek_queue)
        self.algo_list.append('SCAN')
        if self.disk_monitoring:
            self.ShowTrack(seek_queue, "SCAN")

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
        self.QueueSeek(seek_queue)
        self.algo_list.append('C_SCAN')
        if self.disk_monitoring:
            self.ShowTrack(seek_queue, "C_SCAN")

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

        self.QueueSeek(seek_queue)
        self.algo_list.append('LOOK')
        if self.disk_monitoring:
            self.ShowTrack(seek_queue, "LOOK")

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
        self.QueueSeek(seek_queue)
        self.algo_list.append('C_LOOK')
        if self.disk_monitoring:
            self.ShowTrack(seek_queue, "C_LOOK")

    def ShowDiskSpeed(self):
        speed_list_MB = np.array(self.speed_list) / 1000
        # print(self.speed_list, speed_list_MB, 'MB\s')
        # print("DiskSpeed: ","".join([str(int(x)) for x in list(speed_list_MB)]))
        print("DiskSpeed: ", speed_list_MB[-1], "MB/S")

    def ShowTrack(self, seek_queue, algo):
        track_queue = []
        for seek_addr in seek_queue:
            track_queue.append(seek_addr[0])


##############################################
# block存储区块框架功能：  
# 0 存储文件-获取空闲位置
# 1 删除文件-获取文件位置
# 2 文件操作-获取文件位置
##############################################
class Block:
    # init 总共的空间 和空闲空间的起始位置
    def __init__(self, total_space, loc): 
        self.total_space = total_space #总共空间
        self.free_space = total_space  #空闲空间
        self.fp = None #文件起始位置
        self.loc = loc #当前空闲位置

    # 存储文件or删除文件之后要重置空闲位置
    def setFreeSpace(self, free_space): 
        self.free_space = free_space

    # 存储文件之前要获取空闲位置
    def getFreeSpace(self):
        return self.free_space

    # 存储文件or删除文件之后重制文件起始位置
    def setFp(self, fp): #文件开始位置 初始None
        self.fp = fp

    # 存储文件or删除文件or文件操作之前获取当前文件起始位置
    def getFp(self):
        return self.fp

    # 存储文件之前获取当前空闲空间的起始位置
    def getLoc(self):
        return self.loc

##############################################
# FileManager文件管理模块框架功能：
# 0 文件操作指令：
#       ls\cd\mkdir\mkf\rm 已完成
# 1 文件存储地址：
#       相对地址
#       绝对地址
#       相对地址及绝对地址间的转换
# 2 多级目录结构：
#       构建文件存储树
# 3 文件存储填充算法：
#       最先填充算法 已选择
#       最优、最差填充算法 未选择
# 4 文件存储空间管理：
#       位示图法
# 5 文件安全与异常捕捉：
#       对于非法操作进行拦截并发出异常警告
##############################################
class FileManager:
    
    #def __init__(self, block_size=512, tracks=200, secs=12):  # block_size的单位:Byte
    def __init__(self, block_size, tracks, secs, seek_algo, username):

        # os.sep是为了解决不同平台上文件路径分隔符差异问题
        self.file_separator = os.sep
        # os.getcwd() 方法用于返回当前工作目录
        self.root_path = os.getcwd() + self.file_separator + 'SwiftOS_files' + self.file_separator + username  # Win下为\, linux下需要修改!
       
        # 当前工作目录相对路径, 可以与root_path一起构成绝对路径
        #self.current_working_path = self.file_separator + '@' + username + self.file_separator
        self.current_working_path = self.file_separator

        self.block_size = block_size
        self.block_number = tracks * secs
        self.tracks = tracks
        self.secs = secs
        self.seek_algo = seek_algo

        # self.unfillable_block = [3, 6, 9, 17]
        self.unfillable_block = [2,3,4,5,6,9,10,11,12,13,16,17]
        self.block_dir = {}
        self.bitmap = []
        self.all_blocks = self.initBlocks()


        self.file_system_tree = self.fileTree(self.root_path)


        self.disk = Disk(block_size, tracks, secs)

    # return file, if failed, report error and return None.
    # file_path支持绝对路径, mode格式与函数open()约定的相同

    # 获取磁盘寻道的算法
    def getSeekAlgo(self):
        #seek_queue = [(98, 3), (183, 5), (37, 2), (122, 11), (119, 5), (14, 0), (124, 8), (65, 5), (67, 1), (198, 5), (105, 5), (53, 3)]
        seek_queue = [(116, 3), (5, 5), (12, 2), (97, 9), (56, 6)]
  
        if self.seek_algo == 'FCFS':
            self.disk.FCFS(seek_queue)
        elif self.seek_algo == 'SSTF':
            self.disk.SSTF(seek_queue)
        elif self.seek_algo == 'SCAN':
            self.disk.SCAN(seek_queue)
        elif self.seek_algo == 'C_SCAN':
            self.disk.C_SCAN(seek_queue)
        elif self.seek_algo == 'LOOK':
            self.disk.LOOK(seek_queue)
        elif self.seek_algo == 'C_LOOK':
            self.disk.C_LOOK(seek_queue)
        else:
            print("getSeekAlgo: error. '" + seek_algo + "' no such disk seek algorithm")

    # catch e 捕捉打开文件操作中的异常
    def getFileCatchE(self, file_path, mode='r'):
        # 由于open()能完成绝大多数工作, 该函数的主要功能体现在排除异常:
        (upper_path, basename) = self.pathSplit(file_path)
        current_working_dict = self.pathToDictionary(upper_path)
        # 异常1.当路径文件夹不存在时
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
                    seek_queue = self.fpToLoc(file_path)
                    if self.seek_algo == 'FCFS':
                        self.disk.FCFS(seek_queue)
                    elif self.seek_algo == 'SSTF':
                        self.disk.SSTF(seek_queue)
                    elif self.seek_algo == 'SCAN':
                        self.disk.SCAN(seek_queue)
                    elif self.seek_algo == 'C_SCAN':
                        self.disk.C_SCAN(seek_queue)
                    elif self.seek_algo == 'LOOK':
                        self.disk.LOOK(seek_queue)
                    elif self.seek_algo == 'C_LOOK':
                        self.disk.C_LOOK(seek_queue)
                    else:
                        print("get_file: cannot get file '" + basename + "': '" + seek_algo + "' no such disk seek algorithm")
                    
                    f = open(gf_path, mode)
                    # print("get_file success")
                    return json.load(f)
                else:
                    print( "get_file: cannot get file'" + basename + "': dir not a common file")
            else:
                print("get_file: cannot get file'" + basename + "': file not exist")

        return False

    # 递归地构建文件树
    # 文件树采用字典形式 文件名为键
    # 当该文件为文件夹时, 其值为一个字典
    # 当该文件为文件时, 其值为长度为4的字符串, 表示类型 / 读 / 写 / 执行
    def fileTree(self, now_path):  # now_path是当前递归到的绝对路径
        file_list = os.listdir(now_path)
        part_of_tree = {}  # 当前文件夹对应的字典
        for file in file_list:
            file_path = os.path.join(now_path, file)
            if os.path.isdir(file_path):  # 文件夹为键 其值为字典
                part_of_tree[file] = self.fileTree(file_path)
            else:
                with open(file_path) as f:  # 普通文件为键, 其值为该文件的属性
                    # print(file_path)
                    data = json.load(f)
                    part_of_tree[file] = data['type']
                    if self.fileStore(data, file_path[len(self.root_path):]) == -1:  # 将此文件的信息存于外存块中
                        # 没有足够的存储空间
                        print("block storage error: No Enough Initial Space")
        return part_of_tree

    # 按照文件存储方式计算文件绑定的存储块
    def calFileLoc(self, block_num):  # 计算每个文件块所绑定的位置
        track = int(block_num / self.secs)
        sec = block_num % self.secs
        return track, sec

    # 根据输入fp获取其存储位置的列表
    def fpToLoc(self, fp):  # 输入fp，得到其位置list
        # 当fp为相对路径时, 转成绝对路径
        if fp[0] != self.file_separator:
            fp = self.current_working_path + fp
        start, length, size = self.block_dir[fp]
        loc_list = []
        for i in range(start, start + length):
            loc_list.append(self.all_blocks[i].getLoc())
        return loc_list

    # 初始化存储区块
    def initBlocks(self):  # 初始化文件块
        blocks = []  # 块序列
        for i in range(self.block_number):  # 新分配blocks
            b = Block(self.block_size, self.calFileLoc(i))
            blocks.append(b)
        self.bitmap = np.ones(self.block_number)  # 初始化bitmap
        return blocks

    # 寻找连续的num个空闲存储区块 first fit文件填充算法
    def findFreeBlocks(self, num): #, method=0
        goal_str = "".join([str(int(x)) for x in list(np.ones(num))]) # 格式转换 位图ndarray->string
        # goal_str指需要的连续块（bitmap形式）的字串
        bitmap_str = "".join([str(int(x)) for x in list(self.bitmap)]) # 格式转换 位图ndarray->string

        first_free_block = bitmap_str.find(goal_str)
        return first_free_block

    # 文件存入存储区块
    def fileStore(self, f, fp):  # 将此文件的信息存于外存块中, method=0
        num = int(int(f["size"]) / self.block_size)
        occupy = int(f["size"]) % self.block_size
        first_free_block = self.findFreeBlocks(num + 1) #, method
        if first_free_block == -1:  # 没有足够空间存储此文件
            return -1
        free = self.block_size - occupy
        self.block_dir[fp] = (first_free_block, num + 1, int(f["size"]))  # block分配信息存在dir中
        count = int(first_free_block)
        for i in range(num + 1):
            if i == num:  # 最后一块可能有碎片
                self.all_blocks[count].setFreeSpace(free)
            else:
                self.all_blocks[count].setFreeSpace(0)
            self.bitmap[count] = 0
            self.all_blocks[count].setFp(fp)
            count += 1
        return 0

    # 文件从存储区快中删除
    def fileDeletes(self, fp):  # 在文件块中删除文件
        start = self.block_dir[fp][0]
        length = self.block_dir[fp][1]
        for i in range(start, start + length):
            self.all_blocks[i].setFreeSpace(self.block_size)
            self.all_blocks[i].setFp(None)
            self.bitmap[i] = 1
        del self.block_dir[fp]
        return

    # 将 "目录的相对或绝对路径" 转化为 当前目录的字典, 用于之后的判断 文件存在 / 文件类型 几乎所有函数的第一句都是它
    def pathToDictionary(self, dir_path):
        print(dir_path)
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
    def pathSplit(self, path):
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
    # dir_path为空时,列出当前目录文件; 非空(填相对路径时), 列出目标目录里的文件
    def ls(self, dir_path='', mode=''): # , method='print'
        current_working_dict = self.pathToDictionary(dir_path)
        # 异常1:ls路径出错 pathToDictionary()报错
        if current_working_dict == -1:
            pass
        # ls的对象是一个文件，则只显示该文件的信息
        elif not isinstance(current_working_dict, dict): # isinstance() 函数来判断一个对象是否是一个已知的类型
            (upper_path, basename) = self.pathSplit(dir_path)
            if current_working_dict[3] == 'x':
                if mode == '-l' or mode == '-al': # '-l' 要求输出current_working_dict
                    # 特殊颜色
                    print(current_working_dict, '\t', '\033[1;33m' + basename + '\033[0m')
                else:
                    print('\033[1;33m' + basename + '\033[0m', '    ', end='')
            else:
                if mode == '-l' or mode == '-al':
                    print(current_working_dict, '\t', basename)
                else:
                    print(basename,'    ', end='')
        # ls的对象是一个文件夹，则显示文件夹内部的信息
        else:
            file_list = current_working_dict.keys()

            # 目录为空时, 直接结束
            if len(file_list) == 0:
                return
            if mode not in ('-a', '-l', '-al', ''):
                print("ls: invalid option'" + mode + "', try '-a' / '-l' / '-al'")
                return
            for file in file_list:
                # 隐藏文件不显示
                if file[0] == '.' and not mode[0:2] == '-a':
                    pass
                # 文件夹高亮蓝色显示
                elif isinstance(current_working_dict[file], dict):
                    if mode == '-l' or mode == '-al':
                        print('d---', '\t', '\033[1;34;47m' + file + '\033[0m')
                    else:
                        print('\033[1;34;47m' + file + '\033[0m', '    ', end='')
                # 可执行文件高亮红色显示
                elif current_working_dict[file][0] == 'e':
                    if mode == '-l' or mode == '-al':
                        print(current_working_dict[file], '\t', '\033[31m' + file + '\033[0m')
                    else:
                        print('\033[31m' + file + '\033[0m', '    ', end='')
                else:
                    if mode == '-l' or mode == '-al':
                        print(current_working_dict[file], '\t', file)
                    else:
                        print(file, '   ', end='')
            print('')

    # command: cd
    def cd(self, dir_path=''):  # 参数仅支持目录名, 支持相对或绝对路径 之后以path结尾的表示支持相对或绝对路径, 以name结尾的表示仅支持名
        (upper_path, basename) = self.pathSplit(dir_path)
        current_working_dict = self.pathToDictionary(upper_path)
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
                    if basename == "." or basename == ".." or isinstance(current_working_dict[basename], dict):
                        # 相对路径
                        if dir_path[0] != self.file_separator:
                            # 警告! 未解决异常: 当路径以数个\结尾时, \不会被无视.
                            path_with_point = self.current_working_path + dir_path + self.file_separator
                        # 绝对路径
                        else:
                            path_with_point = dir_path + self.file_separator
                        # 消除..和.
                        dir_list = path_with_point.split(self.file_separator)
                        dir_list = [i for i in dir_list if i != '']  # 去除由\分割出的空值
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
        (upper_path, basename) = self.pathSplit(dir_path)
        current_working_dict = self.pathToDictionary(upper_path)  # 将获取到的字典直接赋值, 对其修改可以影响到文件树
        # 异常1 路径出错
        if current_working_dict == -1:
            pass
        else:
            # 异常2 文件已存在
            if basename in current_working_dict:
                print("mkdir error. '" + basename + "' already exists")
            else:
                # 相对路径
                if dir_path[0] != self.file_separator:
                    mkdir_path = self.root_path + self.current_working_path + dir_path
                # 绝对路径
                else:
                    mkdir_path = self.root_path + dir_path
                os.makedirs(mkdir_path)
                current_working_dict[basename] = {}
                print("mkdir success.")

    # command: make file
    def mkf(self, file_path, file_type='crwx', size='120', content=None):
        if file_type[0] != 'c':
            print("mkf: cannot create file'" + file_path + "': only common file can be created")
            return
        (upper_path, basename) = self.pathSplit(file_path)
        current_working_dict = self.pathToDictionary(upper_path)
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
                # 相对路径 先不与self.root_path相拼接, 为了紧接着的fileStore传参
                if file_path[0] != self.file_separator:
                    mkf_path = self.current_working_path + file_path
                # 绝对路径
                else:
                    mkf_path = file_path

                if self.fileStore(json_text, mkf_path) == -1:  # 测试是否能装入block
                    print("mkf: error. No enough Space")
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
                print("mkf: error file'" + basename + "' already exists")

    # command: rm name
    def rm(self, file_path, mode=''):
        (upper_path, basename) = self.pathSplit(file_path)
        current_working_dict = self.pathToDictionary(upper_path)
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
                            sub_dir_dict = self.pathToDictionary(file_path)
                            for i in copy.deepcopy(
                                    copy.deepcopy(list(sub_dir_dict.keys()))):  # 删除此目录下的每个文件
                                sub_file_path = file_path + '\\' + i
                                real_sub_file_path = rmdir_path + '\\' + i
                                # 非空的目录, 需要递归删除
                                if isinstance(sub_dir_dict[i], dict) and sub_dir_dict[i]:
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
                        "rm -r: cannot remove '" + basename + "': this directory is not empty, try to use 'rm -rf [path]'")
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
                            self.fileDeletes(rm_path)
                            rm_path = self.root_path + rm_path
                            # 删真正文件
                            os.remove(rm_path)
                            # 同时修改文件树
                            current_working_dict.pop(basename)
                        # 异常1 文件只读, 不可删除
                        else:
                            print("rm: cannot remove '" + basename + "': file read only, try to use -f option")
                    # 异常2 文件不存在
                    else:
                        print("rm: cannot remove '" + basename + "': No such file")
                # 异常3 文件是目录
                except (PermissionError, KeyError):
                    print("rm: cannot remove '" + basename + "': Is a dir. Try to use -r option")
            else:
                print("rm: invalid option'" + mode + "', try '-r' / '-f' / '-rf'")

    # 将存储的文件树打印出来
    def showFileTree(self, layer=0):
        dir = self.root_path
        listdir = os.listdir(dir) 
        #os.listdir() 方法用于返回指定的文件夹包含的文件或文件夹的名字的列表 它不包括 . 和 .. 即使它在文件夹中

        for file in listdir:
            file_path = os.path.join(dir, file)
            print("|  " * (layer - 1), end="")
            # 文件夹和文件不同方式表示
            print("||||" if os.path.isdir(file_path) else "|>>>", end="") #index == len(listdir) - 1
            print(file)

            # 逐层递归
            if os.path.isdir(file_path):
                self.showFileTree( layer + 1)

    # 打印所有block的状态
    def showBlockStatus(self):
        # 打印总体的block状态
        total = self.block_size * self.block_number  # 总字节数
        all_free = len(np.nonzero(self.bitmap)[0]) #每个区bitmap块存放的为block
        all_free *= self.block_size  # 剩余的总字节数
        all_occupy = total - all_free  # 已占用的总字节数
        print("total: {0} B,\t allocated: {1} B,\t free: {2} B\n".format(total, all_occupy, all_free))
      
        # 打印每个block状态
        for i in range(self.block_number):
            b = self.all_blocks[i]
            occupy = self.block_size - b.getFreeSpace()
            if occupy > 0: 
                print("block #{:<5} {:>5} / {} Byte(s)   {:<20}".format(i, occupy, self.block_size, str(b.getFp()))) #该block起始文件指针

    # 访存时磁头当前位置
    def setNow_headpointer(self, now_headpointer=0):
        self.disk.setNowHeadpointer(now_headpointer)

    # 设置磁盘减慢因子
    def setDiskX_slow(self, x_slow=10):
        self.disk.setX_slow(x_slow)

    # 画出过去所有读写磁盘操作时的平均速度柱状图
    def ShowDiskSpeed(self):
        self.disk.ShowDiskSpeed()


if __name__ == '__main__':
    # 创建一个文件管理的实例化对象
    demo = FileManager(block_size=512, tracks=200, secs=12, seek_algo='FIFO', username='USER')
    # 初始化该对象的初始指针头以及寻道算法
    demo.setNow_headpointer(35) #设置初始指针位置
    demo.getSeekAlgo(seek_algo='FCFS')
    demo.ShowDiskSpeed()
    demo.getSeekAlgo(seek_algo='SSTF')
    demo.ShowDiskSpeed()
    demo.getSeekAlgo(seek_algo='SCAN')
    demo.ShowDiskSpeed()
    demo.getSeekAlgo(seek_algo='C_SCAN')
    demo.ShowDiskSpeed()
    demo.getSeekAlgo(seek_algo='LOOK')
    demo.ShowDiskSpeed()
    demo.getSeekAlgo(seek_algo='C_LOOK')
    demo.ShowDiskSpeed()

    

    # demo.showBlockStatus()
    print("####################")
    # demo.showFileTree()
    