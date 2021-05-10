# coding=utf-8
import numpy as np
from operator import itemgetter, attrgetter
#import seaborn
import pandas as pd
import matplotlib.pyplot as plt
import copy
# 页表
class PageTable:
    """
    脏位：dirty_bit
    存在位：resident_bit
    访问位：reference_bit
    帧号：frame_num
    """
    def __init__(self, page_total=8):
        self.table = self.virtual_memory = np.array(
                [[-1, -1, -1, -1] for i in range(page_total)])

    def insert(self, page_num):
        self.table[page_num] = [0, 1, 0, -1]

    def update(self, page_num, dirty_bit, resident_bit, reference_bit, frame_num):
        self.table[page_num].dirty_bit = dirty_bit
        self.table[page_num].resident_bit = resident_bit
        self.table[page_num].reference_bit = reference_bit
        self.table[page_num].frame_num = frame_num

    def delete(self, page_num):
        self.table[page_num] = [-1, -1, -1, -1]


class MemoryManager:
    def __init__(self, storage_mode, option, page_size=1024, page_total=8,
                 frame_size=1024, frame_total=6):
        """
        :param storage_mode：存储模式
        :param option:当使用连续存储方式时，表示采用的动态分区分配算法；当使用页式存储方式时，表示采用的缺页置换算法
        :param page_size: 虚拟页面大小
        :param page_total: 虚拟页面数量
        :param frame_size: 物理页帧大小
        :param frame_total: 物理页帧数量
        """
        if storage_mode == 'ps':
            # 使用页式分配存储方式
            self.page_size = page_size
            self.page_total = page_total
            self.frame_size = frame_size
            self.frame_total = frame_total
            self.swapping = option
            # 所有进程的页表存为字典，键为进程ID，值为对应页表
            self.all_page_tables = {}
            # 所有进程的页表存为字典，键为进程ID，值为虚拟内存的分配情况
            # self.virtual_memory = {}
            # 用一维数组physical_memory记录物理内存分配情况
            # 初始化为-1
            self.physical_memory = [-1 for i in range(self.frame_total)]
            #访问页面次数
            self.page_access = 0
            # 缺页次数
            self.page_fault = 0
            # 访问序列reference_queue，最近访问的放在队列最后
            self.reference_queue = []
            self.virtual_allocated = 0
            self.virtual_rate = [0]
            self.virtual_total = page_size * page_total
        if storage_mode == 'cs':
            # 使用连续分配存储方式
            self.memory_record = []
            self.free_partition = [[0, frame_total * frame_size]]
            self.allocate_mode = option
        # used for plotting

        # for x axis
        self.x = [0]
        self.storage_mode = storage_mode
        # 已分配的物理内存空间
        self.physical_total = frame_total * frame_size
        self.physical_allocated = 0
        self.physical_rate = [0]
    def allocate_memory(self, process_id, size):
        if self.storage_mode == 'ps':
            return self.allocate_virtual(process_id, size)
        elif self.storage_mode == 'cs':
            return self.allocate_continue(process_id, size)

    def free_memory(self, process_id):
        if self.storage_mode == 'ps':
            return self.free_virtual(process_id)
        elif self.storage_mode == 'cs':
            return self.free_continue(process_id)

    def access_memory(self, process_id, address):
        if self.storage_mode == 'ps':
            return self.access_page(process_id, address)
        elif self.storage_mode == 'cs':
            return self.access_continue(process_id, address)

    def display_memory_status(self):
        if self.storage_mode == 'ps':
            return self.show_page()
        elif self.storage_mode == 'cs':
            return self.show_continue()

    def memory_watching(self):
        if self.storage_mode == 'ps':
            self.memory_watching_page()
        elif self.storage_mode == 'cs':
            self.continue_memory_watching()

    def allocate_virtual(self, process_id, size):
        """
        为进程分配虚拟内存空间
        :param process_id: 进程号
        :param size: 要求分配的空间大小
        """
        if process_id in self.all_page_tables.keys():  # 如果该进程已经建立了页表
            p_table = self.all_page_tables[process_id]  # 取出页表
        else:  # 如果该进程未建页表
            p_table = PageTable()  # 创建一个页表
            self.all_page_tables[process_id] = p_table
        found = 0
        for i in range(self.page_total):  # 寻找一块虚拟内存空间
            if p_table.table[i][3] == -1:
                p_table.insert(i)  # 页表中新插入一项
                found = 1
                if size <= self.page_size:
                    size = 0  # 分配完毕
                    break
                else:
                    size -= self.page_size
        if found == 0:
            print("虚拟空间已满！")
        elif found == 1 and size != 0:
            self.free_virtual(process_id)
        else:
            self.virtual_allocated += size
            print("分配成功！")

    def allocate_continue(self, process_id, size):
        """
        使用best_fit算法为进程分配连续的物理内存空间
        :param process_id: 进程号
        :param size: 要求分配的空间大小
        """
        choose_part = -1
        if self.allocate_mode == "BestFit":  # 最佳适应算法
            choose_part = self.Best_fit(size)
        elif self.allocate_mode == "FirstFit":  # 首次适应算法
            choose_part = self.First_fit(size)
        elif self.allocate_mode == "WorstFit":  # 最坏适应算法
            choose_part = self.Worst_fit(size)
        #  如果找到最小最适合的空闲分区
        if choose_part != -1:
            # 给该进程分配连续的物理内存
            self.physical_allocated += size
            self.memory_record.append([self.free_partition[choose_part][0], size, process_id])
            print("%d号进程物理内存分配成功！" % process_id)
            # 修改空闲分区表
            if self.free_partition[choose_part][1] == size:
                self.free_partition.pop(choose_part)
            else:
                # 修改选择的空闲分区的起始地址和大小
                self.free_partition[choose_part][0] += size
                self.free_partition[choose_part][1] -= size
        # 如果没有找到合适的空闲分区
        elif choose_part == -1:
            # 如果剩余的空闲物理内存不小于请求内存的进程大小, 紧凑法解决外部碎片问题
            if self.physical_total - self.physical_allocated >= size:
                self.memory_compact(size,process_id)
            else:
                print("分配失败：没有空间为%d号进程分配！" % process_id)

    def free_virtual(self, process_id):
        """
        释放某一进程的虚拟内存空间
        :param process_id: 进程号
        """
        if process_id in self.all_page_tables.keys():  # 如果该进程已经建立了页表
            p_table = self.all_page_tables[process_id]  # 取出页表
            for i in range(self.page_total):  # 遍历页表每一项
                if p_table.table[i][1] == 1:  # 若该项存在
                    found = 1
                # 若有对应的物理页，释放物理内存
                    if p_table.table[i][3] != -1:
                        self.physical_memory[p_table.table[i][3]] = -1
                    p_table.delete(i)   # 删除页表项
            print("进程释放空间成功！")
        else:  # 如果该进程未建页表
            print("错误：没有为%d号进程分配虚拟内存" % process_id)

    def free_continue(self, process_id):
        """
        在连续分配存储模式下释放某一进程的物理内存空间
        :param process_id: 进程号
        """
        found = -1  # 用来记录是否在物理内存中找到需要释放的进程

        for i in range(len(self.memory_record)):
            if self.memory_record[i][2] == process_id:
                found = 1
                start_address = self.memory_record[i][0]
                process_size = self.memory_record[i][1]
                self.physical_allocated -= self.memory_record[i][1]
                self.memory_record.pop(i)
                break
        if found != -1:
            before_part = -1  # 用来记录与被释放的进程的物理内存起始地址处相连的空闲分区
            after_part = -1  # 用来记录与被释放的进程的物理内存终止地址处相连的空闲分区
            for i in range(len(self.free_partition)):
                if self.free_partition[i][0] + self.free_partition[i][1] == start_address:
                    before_part = i
                elif self.free_partition[i][0] == start_address + process_size:
                    after_part = i
            # 合并新的空闲分区
            # 如果被释放的进程在两个空闲分区之间
            if before_part != -1 and after_part != -1:
                self.free_partition[before_part][1] += process_size + self.free_partition[after_part][1]
                self.free_partition.pop(after_part)
            # 如果被释放的进程之前有一个空闲分区
            elif before_part != -1:
                self.free_partition[before_part][1] += process_size
            # 如果被释放的进程之后有一个空闲分区
            elif after_part != -1:
                self.free_partition[after_part][0] = start_address
                self.free_partition[after_part][1] += process_size
            else:
                self.free_partition.append([start_address, process_size])
            print("%d号进程释放空间成功！"% process_id)
        else:  # 如果没有在物理内存中找到被要求释放的进程
            print("释放错误：没有为%d号进程分配物理内存" % process_id)

    def access_page(self, process_id, address):
        """
        访问一个进程的地址空间内的地址（此地址为经过转换的线性地址）,做安全检查（实际是MMU的工作？）
        :param process_id: 进程号
        :param address: 要访问的地址
        :return: 若成功，返回对应的物理地址；若失败，返回false
        """
        self.page_access += 1
        if process_id in self.all_page_tables.keys():  # 如果该进程已经建立了页表
            p_table = self.all_page_tables[process_id]  # 获得该进程页表

            idx = address // self.page_size
            if idx < self.page_total:
                if p_table.table[idx][1] == 1:  # 若该项存在
                    # 若有对应的物理页，可正常访问
                    offset = address % self.page_size  # 页内偏移
                    if p_table.table[idx][3] != -1:
                        p_table.table[idx][2] = 1  # 访问位置1

                        # 若已经调入内存，只需要改变虚拟页的访问队列
                        self.reference_queue.remove(idx)
                        self.reference_queue.append(idx)
                        physical_address = self.frame_size * self.physical_memory[p_table.table[idx][3]] + offset
                        print("访问成功！物理地址为0x%-5x" % physical_address)
                        return physical_address

                    # 若访问的虚拟页没有分配物理页，进入按需调页（demanding paging)
                    elif self.swapping == 'LRU':
                        self.page_fault += 1  # 缺页次数+1
                        physical_address = self.frame_size * self.LRU(idx, p_table, process_id) + offset
                        print("访问成功！物理地址为0x%-5x" % physical_address)
                    elif self.swapping == 'FIFO':
                        self.page_fault += 1  # 缺页次数+1
                        physical_address = self.frame_size * self.FIFO(idx, p_table, process_id) + offset
                        print("访问成功！物理地址为0x%-5x" % physical_address)
                    else:
                        pass  # 待后续加入更多算法
                else:
                    print("地址访问错误！")
                    return False
            else:
                print("地址访问错误！")
                return  False
        else:  # 如果该进程没有页表
            print("释放错误：没有为该进程分配虚拟内存!")
            return False

    def access_continue(self, process_id, address):
        """
        在连续分配存储模式下访问某一进程的逻辑地址，实现逻辑地址到物理地址的转换
        :param process_id: 进程号
        :param address: 访问该进程的逻辑地址
        :return: 若成功，返回对应的物理地址；若失败，返回false
        """
        found = -1  # 用来记录访问进程是否在物理内存中
        for i in range(len(self.memory_record)):
            if self.memory_record[i][2] == process_id:
                found = 1
                if address > self.memory_record[i][1] or address < 0:
                    print("访问错误：进程地址访问越界！")
                    return False
                else:
                    physical_address = self.memory_record[i][0]+address
                    print("访问成功！物理地址为0x%-5x" % physical_address)
                    return physical_address
        if found == -1:
            print("访问错误：没有为%d号进程分配物理内存" % process_id)
            return False

    def Best_fit(self, size):
        """
        动态分区分配最佳适应算法
        :param size: 进程的大小
        :return: 选择的大小能满足要求的空闲分区号
        """
        choose_part = -1
        # 空闲分区以容量递增次序排列
        sorted(self.free_partition, key=itemgetter(1), reverse=False)
        for i in range(len(self.free_partition)):
            if size <= self.free_partition[i][1]:
                choose_part = i
                break
        return choose_part

    def First_fit(self, size):
        """
        动态分区分配的首次适应算法
        :param size: 进程的大小
        :return: 选择的大小能满足要求的空闲分区号
        """
        choose_part = -1
        # 空闲分区以地址递增次序排列
        sorted(self.free_partition, key=itemgetter(0), reverse=False)
        for i in range(len(self.free_partition)):
            if size <= self.free_partition[i][1]:
                choose_part = i
                break
        return choose_part

    def Worst_fit(self, size):
        """
        动态分区分配的最坏适应算法
        :param size: 进程的大小
        :return: 选择的大小能满足要求的空闲分区号
        """
        choose_part = -1
        # 空闲分区以容量递减次序排列
        sorted(self.free_partition, key=itemgetter(1), reverse=True)
        for i in range(len(self.free_partition)):
            if size <= self.free_partition[i][1]:
                choose_part = i
                break
        return choose_part

    def memory_compact(self, size, process_id):
        """
        紧凑法解决物理内存外部碎片问题
        :param size: 进程大小
        :param process_id: 进程号
        """
        # 将物理内存中存储的进程按起始地址递增排序
        sorted(self.memory_record, key=itemgetter(0), reverse=False)
        self.memory_record[0][0] = 0  # 将存储的第一个进程起始地址修改成物理内存起始地址
        # 将各个进程连续存储在物理内存，从而合并小的内存碎片
        for i in range(1, len(self.memory_record)):
            fore_staddr = self.memory_record[i - 1][0]
            fore_size = self.memory_record[i - 1][1]
            self.memory_record[i][0] = fore_staddr + fore_size
        addr = self.memory_record[i][0] + self.memory_record[i][1]
        self.free_partition.clear()  # 清空空闲分区表
        # 空闲分区表记录存入新进程后的空闲分区
        self.free_partition.append([addr + size, self.physical_total - self.physical_allocated - size])
        self.memory_record.append([addr, size, process_id])  # 更新物理内存记录
        self.physical_allocated += size
        print("%d号进程物理内存分配成功！" % process_id)

    def LRU(self, page_num, p_table, p_id):
        """
        :param p_id: 进程号
        :param page_num: 发生缺页的虚拟页号
        :param p_table: 对应进程的页表
        :return: 分配的物理页号
        """
        # 若还有空闲的物理页
        if -1 in self.physical_memory:
            p_table.table[page_num][3] = self.physical_memory.index(-1)  # 存入帧号
            self.physical_memory[self.physical_memory.index(-1)] = p_id  # 写入物理内存
            self.physical_allocated += self.frame_size
            self.reference_queue.append(page_num)  # 将该虚拟页加入访问队列
            p_table.table[page_num][2] = 1  # 访问位置1
            return p_table.table[page_num][3]
        # 换页
        else:
            frame_num = p_table.table[self.reference_queue[0]][3]  # 取出最久未访问的虚拟页号对应的物理页号
            past_p_id = self.physical_memory[frame_num]  # 取出被换出的页属于的进程
            past_p_table = self.all_page_tables[past_p_id]  # 取出被换出的页属于的进程的页表
            past_p_table.table[page_num][3] = -1  # 改写该虚拟页对应的页表项中的帧号

            self.physical_memory[frame_num] = p_id  # 模拟重写物理内存
            self.reference_queue.pop(0)  # 页面访问队列删除第一个
            self.reference_queue.append(page_num)  # 加入新换入的页
            p_table.table[page_num][3] = frame_num  # 改写该虚拟页对应的页表项中的帧号
            p_table.table[page_num][2] = 1  # 访问位置1
            return frame_num

    def FIFO(self, page_num, p_table, p_id):
        """
        :param p_id: 进程号
        :param page_num: 发生缺页的虚拟页号
        :param p_table: 对应进程的页表
        :return：分配的物理页号
        """
        # 若还有空闲的物理页
        if -1 in self.physical_memory:
            p_table.table[page_num][3] = self.physical_memory.index(-1)  # 存入帧号
            self.physical_memory[self.physical_memory.index(-1)] = p_id  # 写入物理内存
            self.physical_allocated += self.frame_size
            self.reference_queue.append(page_num)  # 将该虚拟页加入访问队列
            p_table.table[page_num][2] = 1  # 访问位置1
            return p_table.table[page_num][3]
        # 换页
        else:
            frame_num = p_table.table[self.reference_queue[0]][3]  # 取出最早进入的虚拟页号对应的物理页号
            past_p_id = self.physical_memory[frame_num]  # 取出被换出的页属于的进程
            past_p_table = self.all_page_tables[past_p_id]  # 取出被换出的页属于的进程的页表
            past_p_table.table[page_num][3] = -1  # 改写该虚拟页对应的页表项中的帧号

            self.physical_memory[frame_num] = p_id  # 模拟重写物理内存
            self.reference_queue.pop(0)  # 页面访问队列删除第一个
            self.reference_queue.append(page_num)  # 加入新换入的页
            p_table.table[page_num][3] = frame_num  # 改写该虚拟页对应的页表项中的帧号
            p_table.table[page_num][2] = 1  # 访问位置1
            return frame_num
    # 打印页表
    def show_page(self):
        for i in self.all_page_tables.keys():
            p_id = i
            p_table = self.all_page_tables[p_id]
            for j in range(self.page_total):
                if p_table.table[j][1] != 0:
                    print("process_id = %3d  page_num = %3d frame_num = %3d" % (p_id, j, p_table.table[j][3]))

    def show_continue(self):
        print('total: %-dB allocated: %-dB free: %-dB' % (self.physical_total, self.physical_allocated,
                                                          self.physical_total - self.physical_allocated))
        for i in range(len(self.memory_record)):
            print('# [start address]: 0x%-5x  [end address]: 0x%-5x pid = %-3d ' % (self.memory_record[i][0],
                                                                                             self.memory_record[i][0] + self.memory_record[i][1],
                                                                                        self.memory_record[i][2]))
    def memory_watching_page(self):
        plt.close("all")
        self.physical_rate.append(self.physical_allocated /self.physical_total)
        self.virtual_rate.append(self.virtual_allocated / self.virtual_total)
        if len(self.x) < 20:
            self.x.append(self.x[-1] + 1)
        else:
            self.x.pop(0)
            self.x.append(self.x[-1] + 1)

        # fixed a bug: divided by zero
        if self.page_access == 0:
            page_fault_rate = 0.0
        else:
            page_fault_rate = self.page_fault / self.page_access
        plt.title(
            "memory access:%d times,page_fault rate:%.2f" % (self.page_access, page_fault_rate))
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.ylim(0, 1.1)
        if len(self.physical_rate) > 20:
            plt.plot(self.x, self.physical_rate[-20:], label='physical', c='r', marker='.')
            plt.plot(self.x, self.virtual_rate[-20:], label='virtual', c='b', marker='.')
        else:
            plt.xticks(self.x)
            plt.plot(self.x, self.physical_rate[-20:], label='physical', c='r', markerfacecolor='b',marker='.')
            plt.plot(self.x, self.virtual_rate[-20:], label='virtual', c='b', markerfacecolor='r',marker='.')
        plt.legend(['physical', 'virtual'], loc=1)

        plt.savefig('memory.jpg')
        # plt.show()

    def continue_memory_watching(self):
        plt.close()
        self.physical_rate.append(self.physical_allocated / self.physical_total)
        if len(self.x) < 20:
            self.x.append(self.x[-1] + 1)
        else:
            self.x.pop(0)
            self.x.append(self.x[-1] + 1)
        plt.xticks(self.x)
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.ylim(0, 1.1)
        if len(self.physical_rate) > 20:
            plt.plot(self.x, self.physical_rate[-20:], label='physical', c='r', markerfacecolor='b', marker='.')
        else:
            plt.plot(self.x, self.physical_rate, label='physical', c='r', markerfacecolor='b', marker='.')
        plt.legend(['memory'])
        #plt.show()
        plt.savefig('memory.jpg')
if __name__ == '__main__':
    memory_manager = MemoryManager(storage_mode='ps', option="LRU")
    memory_manager.allocate_memory(0, 1024)
    memory_manager.display_memory_status()
    memory_manager.allocate_memory(1, 2000)
    memory_manager.display_memory_status()
    memory_manager.allocate_memory(2, 1094)
    memory_manager.access_memory(1, 1024)
    memory_manager.memory_watching()
    memory_manager.access_memory(1, 150)
    memory_manager.memory_watching()
    memory_manager.access_memory(1, 890)
    memory_manager.memory_watching()
    memory_manager.access_memory(2, 1000)
    memory_manager.memory_watching()
    memory_manager.access_memory(1, 1999)
    memory_manager.memory_watching()
    memory_manager.display_memory_status()
    # memory_manager.free(2, t1)
    memory_manager.display_memory_status()
    memory_manager.memory_watching()
    memory_manager.allocate_memory(3, 2026)
    memory_manager.memory_watching()
    memory_manager.access_memory(3, 2000)
    memory_manager.memory_watching()
    memory_manager.access_memory(0, 100)
    memory_manager.memory_watching()
    memory_manager.access_memory(2, 1030)
    memory_manager.memory_watching()
    memory_manager.display_memory_status()
    memory_manager.memory_watching()
    #t2 = memory_manager.allocate_memory(1, 120)
    memory_manager.access_memory(1, 1020)
    memory_manager.memory_watching()
    memory_manager.display_memory_status()
    memory_manager.memory_watching()
    memory_manager.allocate_memory(1, 200)
    memory_manager.memory_watching()
    #memory_manager.free_memory(1, t2)
    #memory_manager.memory_watching()
    memory_manager.display_memory_status()
