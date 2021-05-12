import time
from config import *
import numpy as np
import logging

class Printer(object):
    def __init__(self):
        self.printer_num = printer_num_conf
        logging.basicConfig(level=logging.INFO,
                    filename='log.txt',
                    filemode='w', # w就是写模式，a是追加模式
                    format='%(asctime)s - %(message)s')


    def print_resource_status(self):
        """ 获取设备资源状态 """
        if self.printer_num == printer_num_conf:
            print(f'No Printer is using,there are {self.printer_num} Printer is free')
        else:
            print(f'{self.printer_num} Printer is using')


    def io_device_handler(self, waiting_queue, io_completion):
        while True:
            # 从waiting队列调度任务进行io
            if waiting_queue:
                pid = waiting_queue[0][0]
                wait_time = waiting_queue[0][0]
                # 处理打印机任务
                waiting_queue.pop(0)
                self.printer_num -= 1
                time.sleep(wait_time)

                # io完成
                self.printer_num += 1
                logging.info(f'[pid {pid}] process I/O successfully.')
                io_completion(pid)        


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
        print("[Access Disk] Time total: ", round(this_time_time * 1000, 5), "ms")
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