# coding=utf-8
import numpy as np
import seaborn
import pandas as pd
import matplotlib.pyplot as plt
import copy


class PageTable:
    def __init__(self):
        # frame number represent the virtual page's location in physical memory
        # the table has a k_v as (page, [frame_number, validation])
        self.table = {}
        self.max_address = None

    def insert(self, page_num):  # allocated virtual page number
        self.table[page_num] = [None, -1]

    def delete(self, page_num):  # free virtual page number
        self.table.pop(page_num)

    def transform(self, address, page_size):
        """
        :param address: the visited relative address
        :param page_size: size of each page
        :return: if find valid,return the physical_page_number, else return -1
        """
        idx = address // page_size  # 页表偏移量
        if idx < len(self.table):
            index = list(self.table.keys())[idx]  # 虚页号
            return index
        else:
            return -1

    # when the virtual page being schedule in/out the physical memory
    def modify(self, pnum, fnum, valid):
        """
        :param pnum: which virtual page to modify
        :param fnum: the frame number to add
        :param valid: if this virtual page in physical memory. = 1 in/ -1 not
        """
        if valid == 1:
            self.table[pnum] = [fnum, valid]
        else:
            self.table[pnum][1] = valid


class MemoryManager:
    def __init__(self, mode, page_size=1024, page_number=8,
                 physical_page=3, schedule='FIFO'):
        """
        :param mode: to define the way to allocate the memory
        :param page_size: the size of each page(useful when mode == 'p')
        :param page_number: the total page num of the virtual memory
        :param physical_page: the total page num of the physical memory
        """
        if mode == 'p':
            # record the virtual memory
            self.virtual_memory = np.array(
                [[page_size, -1, 0] for i in range(page_number)])
            # record = np.zeros((physical_page, 2))
            self.physical_memory = [-1 for i in range(physical_page)]
            # for LRU algorithm, the first one is the Least Recent Used, the
            # last is recently visited
            self.schedule_queue = []
            self.ps = page_size
            self.pn = page_number
            self.ppn = physical_page  # the number of physical page
            # record the page table of all the process, has a k_v as (pid:
            # PageTable)
            self.page_tables = {}
            self.schedule = schedule
        elif mode == 'cb':
            '''cb: continuous best fit algorithm
                r: [start_address, size, pid, aid]
                hole: [start_address, size]
                    '''
            self.r = []  # record for memory status
            # record for the empty memory
            self.hole = [[0, page_size * page_number]]
        self.mode = mode
        self.cur_aid = 0  # record every allocation
        self.total = page_number * page_size
        self.allocated = 0
        self.physicalsize = 0

        # used for plotting
        self.virtual_rate = [0]
        # for x axis
        self.x = [0]
        if mode == 'p':
            self.physical_rate = [0]
            self.physical_history = [copy.deepcopy(self.physical_memory)]
            self.page_fault = 0
            self.page_access = 0

    # load executable file into memory
    # if failed, report error and return -1
    def alloc(self, pid, size):
        if self.mode == 'p':
            return self.page_alloc(pid, size)
        elif self.mode == 'cb':
            return self.continue_alloc(pid, size)

    # pid and aid not all be None
    # return True or False, if failed, report error
    def free(self, pid, aid=None):
        if self.mode == 'p':
            return self.page_free(pid, aid)
        elif self.mode == 'cb':
            return self.continue_free(pid, aid)

    # command: dms
    # print status of all pages
    def display_memory_status(self):
        # e.g.
        if self.mode == 'p':
            self.page_show()
        elif self.mode == 'cb':
            self.continue_show()

    def access(self, pid, address):
        if self.mode == 'p':
            self.page1_access(pid, address)
        elif self.mode == 'cb':
            self.continue_access(pid, address)

    # if the memory has the page structure
    def page_alloc(self, pid, size):
        s = size
        aid = self.cur_aid
        self.cur_aid += 1
        for i in range(self.pn):
            if self.virtual_memory[i][1] == -1:  # the page is empty
                self.virtual_memory[i][1] = pid
                if pid in self.page_tables.keys():  # the process has a page table
                    ptable = self.page_tables[pid]
                else:  # the precess does not has a page table
                    ptable = PageTable()  # create one
                    self.page_tables[pid] = ptable
                ptable.insert(i)  # add the virtual page
                if s >= self.ps:
                    self.virtual_memory[i][0] = self.ps
                    s -= self.ps
                else:
                    self.virtual_memory[i][0] = s
                    s -= s
                self.virtual_memory[i][2] = aid
            if s == 0:
                self.allocated += size
                break
        # if the file cannot be loaded into memory then free the above
        # allocation
        if s > 0:
            self.page_free(pid, aid)
            return -1
        # if the file be loaded successfully
        return aid

    # using best-fit algorithm
    def continue_alloc(self, pid, size):
        aid = self.cur_aid
        self.cur_aid += 1
        fit = 1e5  # record the minimum hole size to load the file
        besti = -1  # record the best hole to put the file
        # find the best hole
        for i in range(len(self.hole)):
            if size <= self.hole[i][1] < fit:
                besti = i
                fit = self.hole[i][1]
        # if found
        if besti != -1:
            # add the allocation to record
            self.allocated += size
            self.r.append([self.hole[besti][0], size, pid, aid])
            # if the file size == hole size
            if self.hole[besti][1] == size:
                self.hole.pop(besti)
            else:
                # modify the hole's start_address, size
                self.hole[besti][0] += size
                self.hole[besti][1] -= size
            return aid
        # if not found
        else:
            return -1

    # using best fit algorithm
    def continue_free(self, pid, aid):
        status = 0  # if the pid with aid were found in memory
        delete = []
        for i in range(len(self.r)):
            if (self.r[i][-1] == aid or aid is None) and self.r[i][-2] == pid:
                base_address = self.r[i][0]
                size = self.r[i][1]
                self.allocated -= size
                delete.append(i)
                status = 1
                '''base_meet: if the start address of the new free memory meet with the end of a hole
                                            base_meet = the index of the hole
                                end_meet: if the end address of the new free memory meet with the start of a hole
                                          end_meet = the index of the hole
                            '''
                base_meet = -1
                end_meet = -1
                for i in range(len(self.hole)):
                    if self.hole[i][0] + self.hole[i][1] == base_address:
                        base_meet = i
                    elif self.hole[i][0] == base_address + size:
                        end_meet = i
                # the new free in between of two hole
                if base_meet != -1 and end_meet != -1:
                    self.hole[base_meet][1] += size + self.hole[end_meet][1]
                    self.hole.pop(end_meet)
                # the new free after a hole
                elif base_meet != -1:
                    self.hole[base_meet][1] += size
                # the new free before a hole
                elif end_meet != -1:
                    self.hole[end_meet][1] += size
                    self.hole[end_meet][0] = base_address
                else:
                    self.hole.append([base_address, size])
        if status != 1:
            print("error: the memory does not exist")
            return False
        for i in range(len(delete) - 1, -1, -1):
            self.r.pop(delete[i])
        return True

    # find the aiming page and delete it from page table
    def page_free(self, pid, aid):
        # print('chenbin: debug', 'pid', pid, 'aid', aid)
        status = 0
        for i in range(self.pn):
            if self.virtual_memory[i][1] == pid and (
                    self.virtual_memory[i][2] == aid or aid is None):
                status = 1

                if i in self.physical_memory:  # if the page in physical memory, free it.
                    self.physical_memory[self.physical_memory.index(i)] = -1
                    self.physicalsize -= self.virtual_memory[i][0]
                    self.schedule_queue.remove(i)

                # to delete the process's page item
                ptable = self.page_tables[pid]
                ptable.delete(i)

                # to free it from virtual memory.
                self.allocated -= self.virtual_memory[i][0]
                self.virtual_memory[i][0] = self.ps
                self.virtual_memory[i][1] = -1
                self.virtual_memory[i][2] = 0

        if status == 0:
            # print("error! That memory not Found.")
            return False
        return True

    def page1_access(self, pid, address):
        '''
        :param pid: the process to visit
        :param address: the relative address of the process
        '''
        self.page_access += 1  # plus 1 every time you access a page
        page_offset = address % self.ps  # the offset within the page

        # print('chenbin: debug', 'pid', pid, 'address', address)

        ptable = self.page_tables[pid]  # get the page table to be visited
        # calculate the exact page to be visited
        virtual_pageID = ptable.transform(address, self.ps)

        if virtual_pageID == - \
                1 or self.virtual_memory[virtual_pageID][0] < page_offset:
            # if not existed or the offset illegal
            print("ERROR ADDRESS !!!!")
            return

        if self.schedule == 'LRU':
            self.LRU(virtual_pageID, ptable)
        elif self.schedule == 'FIFO':
            self.FIFO(virtual_pageID, ptable)
        pass  # more algorithm to be continued

    def continue_access(self, pid, address):
        virtual_memory = pd.DataFrame(
            self.r,
            columns=[
                'start_address',
                'size',
                'pid',
                'aid'])
        memory = virtual_memory[virtual_memory['pid'] == pid]
        memory = memory.sort_values('start_address')
        delta, i = address, 0
        while delta > 0 and i < memory.shape[0]:
            delta -= memory.iloc[i]['size']
            i += 1
        if delta > 0:
            print('Error, memory access not found!')

    def LRU(self, pnum, ptable):
        """
        :param pnum: the virtual page to be switched in physical memory
        :param ptable: the ptable records the virtual page
        """
        if ptable.table[pnum][1] == 1:  # the visiting page in physical memory, just change queue
            self.schedule_queue.remove(pnum)
            self.schedule_queue.append(pnum)

        elif -1 in self.physical_memory:  # the memory is still available
            self.physical_memory[self.physical_memory.index(-1)] = pnum
            self.physicalsize += self.virtual_memory[pnum][0]
            self.schedule_queue.append(pnum)  # enlarge queue
            ptable.modify(
                pnum,
                self.physical_memory.index(pnum),
                1)  # modify the page table
            self.page_fault += 1  # page_fault ++

        else:  # switch page
            # always switch out the first in the queue
            index = self.physical_memory.index(self.schedule_queue[0])
            self.physical_memory[index] = pnum
            pid = self.virtual_memory[self.schedule_queue[0]][2]

            # modify the physical memory status
            self.physicalsize -= self.virtual_memory[self.schedule_queue[0]][0]
            self.physicalsize += self.virtual_memory[pnum][0]
            self.page_fault += 1  # page_fault ++

            # change the page table and modify the queue
            p1 = self.page_tables[pid]
            p1.modify(self.schedule_queue[0], 0, -1)
            self.schedule_queue.pop(0)
            self.schedule_queue.append(pnum)
            ptable.modify(pnum, index, 1)

    def FIFO(self, pnum, ptable):
        """
        :param pnum: the virtual page to be switched in physical memory
        :param ptable: the ptable records the virtual page
        :return:
        """
        if ptable.table[pnum][1] != 1 and -1 in self.physical_memory:
            self.physical_memory[self.physical_memory.index(-1)] = pnum
            self.physicalsize += self.virtual_memory[pnum][0]
            self.schedule_queue.append(pnum)  # enlarge queue
            ptable.modify(
                pnum,
                self.physical_memory.index(pnum),
                1)  # modify the page table
            self.page_fault += 1  # page_fault ++
        elif ptable.table[pnum][1] != 1:
            # always switch out the first in the queue
            index = self.physical_memory.index(self.schedule_queue[0])
            self.physical_memory[index] = pnum
            pid = self.virtual_memory[self.schedule_queue[0]][2]

            # modify the physical memory status
            self.physicalsize -= self.virtual_memory[self.schedule_queue[0]][0]
            self.physicalsize += self.virtual_memory[pnum][0]
            self.page_fault += 1  # page_fault ++

            # change the page table and modify the queue
            p1 = self.page_tables[pid]
            p1.modify(self.schedule_queue[0], 0, -1)
            self.schedule_queue.pop(0)
            self.schedule_queue.append(pnum)
            ptable.modify(pnum, index, 1)

    def page_show(self):
        print('total: %-dB allocated: %-dB free: %-dB' % (self.total, self.allocated,
                                                          self.total - self.allocated))
        for i in range(self.pn):
            if self.virtual_memory[i][1] != - \
                    1 and self.virtual_memory[i][2] != -1:
                print(
                    "block #%d  %-4d/%-4d Byte(s)  pid =%-3d  aid =%-3d" % (i, self.virtual_memory[i][0], self.ps,
                                                                            self.virtual_memory[i][1],
                                                                            self.virtual_memory[i][2]))

    def continue_show(self):
        print('total: %-dB allocated: %-dB free: %-dB' % (self.total, self.allocated,
                                                          self.total - self.allocated))
        for i in range(len(self.r)):
            print('# [base address]: 0x%-5x  [end address]: 0x%-5x pid = %-3d aid = %-3d' % (self.r[i][0],
                                                                                             self.r[i][0] + self.r[i][
                                                                                                 1],
                                                                                             self.r[i][2],
                                                                                             self.r[i][3]))

    def memory_watching(self):
        if self.mode == 'p':
            self.memory_watching_page()
        else:
            self.continue_memory_watching()

    def memory_watching_page(self):
        plt.close("all")
        self.physical_rate.append(self.physicalsize / (self.ps * self.ppn))
        self.virtual_rate.append(self.allocated / self.total)
        if len(self.x) < 10:
            self.x.append(self.x[-1] + 1)
        else:
            self.x.pop(0)
            self.x.append(self.x[-1] + 1)
        temp = []
        for i in self.physical_memory:
            temp.append(self.virtual_memory[i][1])
        if len(self.physical_history) < 10:
            self.physical_history.append(temp)
        else:
            self.physical_history.pop(0)
            self.physical_history.append(temp)

        f, (ax1, ax2) = plt.subplots(figsize=(6, 10), nrows=2)

        ax1.set_xticks(self.x)
        ax1.set_ylim(0, 1)
        ax1.set_yticks(np.arange(0, 1.1, 0.1))

        # fixed a bug: divided by zero
        if self.page_access == 0:
            page_fault_rate = 0.0
        else:
            page_fault_rate = self.page_fault / self.page_access

        ax1.set_title(
            '%.2f memory access, page_fault rate %.2f' %
            (self.page_access, page_fault_rate))

        if len(self.physical_rate) > 10:
            ax1.plot(self.x, self.physical_rate[-10:], label='physical', c='r')
            ax1.plot(self.x, self.virtual_rate[-10:], label='virtual', c='b')
        else:
            ax1.set_xticks(self.x)
            ax1.plot(self.x, self.physical_rate, label='physical', c='r')
            ax1.plot(self.x, self.virtual_rate, label='virtual', c='b')
        ax1.legend(['physical', 'virtual'], loc=1)

        physical_memory = pd.DataFrame(
            self.physical_history, columns=[
                '#frame %d' %
                i for i in range(
                    self.ppn)])

        physical_memory = pd.DataFrame(physical_memory.values.T, index=physical_memory.columns,
                                       columns=self.x)
        seaborn.heatmap(data=physical_memory, cbar=None, ax=ax2, annot=True,
                        linewidths=0.5, robust=True)
        plt.tight_layout()
        plt.savefig('memory.jpg')
        # plt.show()

    def continue_memory_watching(self):
        plt.close()
        self.virtual_rate.append(self.allocated / self.total)
        if len(self.x) < 10:
            self.x.append(self.x[-1] + 1)
        else:
            self.x.pop(0)
            self.x.append(self.x[-1] + 1)
        plt.xticks(self.x)
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.ylim(0, 1.1)
        if len(self.virtual_rate) > 10:
            plt.plot(self.x, self.virtual_rate[-10:], c='b')
        else:
            plt.plot(self.x, self.virtual_rate, c='b')
        plt.legend(['memory'])
        plt.savefig('memory.jpg')
        # plt.show()


if __name__ == '__main__':
    mm = MemoryManager(mode='cb')
    t = mm.alloc(0, 200)
    mm.display_memory_status()
    mm.alloc(1, 2000)
    mm.display_memory_status()
    t1 = mm.alloc(2, 1094)
    mm.access(1, 1024)
    mm.memory_watching()
    mm.access(1, 150)
    mm.memory_watching()
    mm.access(1, 890)
    mm.memory_watching()
    mm.access(2, 1000)
    mm.memory_watching()
    mm.access(1, 1999)
    mm.memory_watching()
    mm.display_memory_status()
    # mm.free(2, t1)
    mm.display_memory_status()
    mm.memory_watching()
    mm.alloc(3, 2456)
    mm.memory_watching()
    mm.access(3, 2000)
    mm.memory_watching()
    mm.access(0, 100)
    mm.memory_watching()
    mm.access(2, 1030)
    mm.memory_watching()
    mm.display_memory_status()
    mm.memory_watching()
    t2 = mm.alloc(1, 120)
    mm.access(1, 1020)
    mm.memory_watching()
    mm.display_memory_status()
    mm.memory_watching()
    mm.alloc(1, 200)
    mm.memory_watching()
    mm.free(1, t2)
    mm.memory_watching()
    mm.display_memory_status()
