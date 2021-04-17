# 进程管理python模拟

## 一、PCB

**类结构**

```python
class PCB(object):
    """ ProcessControlBlock
    Atrributes:
        pid,pname,parentid,priority,create_time,status,
        tasklist: 该进程待执行的任务
        msize: 该进程所占用的内存大小
    """
    def __init__(self, pid, pname, priority, content, msize):
        self.pid = pid
        self.pname = pname
        self.priority = priority  # 0 is higher than 1
        self.msize = msize
        self.parent_id = -1
        self.child_pid_list = []    
        self.create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        self.status = 'ready'

        self.tasklist = []
        for task in content:
            info = str.split(task)  
            if len(info) > 1:
                info[1] = int(info[1])
            self.tasklist.append(info)  # example: [[printer, 18], [cpu, 170]]
        self.current_task = -1
```



## 二、管理进程

### 2.1 类结构

```python
class ProcessManager(object):
    """ Provide functions to manage process"""
    def __init__(self, memory_manager, time_slot=1, priority=True):
        """ 
        Args:
            pid_no: 下个进程的序号
            pcblist: 被管理进程的PCB
            ready_quene: 就绪队列，分为三个优先级
            waiting_quene:等待队列
            p_running：正在运行的进程，同一时间只有一个
            memory_manager: 每个进程所对应的内存及其管理器
            mem_of_pid：每个进程所对应的内存号
        """
        self.pid_no = 0
        self.pcblist = []
        self.ready_quene = [[] for i in range(3)]
        self.waiting_quene = []
        self.p_running = None
        self.memory_manager=memory_manager
        self.time_slot=time_slot
        self.priority=priority
        self.mem_of_pid = {}
```



### 2.2 进程创建

两种方式：执行命令创建、由父进程fork

 **create()**函数：exec文件创建 

 **fork()** 函数：创建子进程

**流程：**

- 初始化PCB
  - create创建pcb对象
  - fork使用deepcopy
- 该进程的PCB加入pcblist，统一管理
- pid进入就绪队列（优先级由属性priority确定）
- 字典 mem_of_pid 记录进程对应的内存信息



### 2.3 进程调度

#### **调度方式**

- 优先级队列+时间片

- 二者结合=多级反馈队列  √

  

#### 相关函数

**dispatch()**

功能：调度进程使其从ready->running

**流程：**

- 从ready队列中取出进程
- 该进程状态置为running
- 若ready队列无元素，则进程运行标志设-1



**timeout()**

功能：时间片用尽，running->ready/terminate

**流程：**

- 若该进程在时间片内已执行完task，则进程正常结束

- 若task未结束，则又进入ready队列等待被调度

- 执行dispatc()继续调度进程

​	

### 2.4 阻塞与唤醒

**io_wait()**

功能：

**流程：**

- 



**io_completion()**

功能：

**流程：**

- 


### 2.5 结束进程

**kill_process()**

功能：

**流程：**

- 正常kill
  - 判断状态，从队列中取出pcb
  - kill其所有子进程
  - 释放资源
- 异常结束
  - try catch错误信息处理



## 三、运行逻辑

> 如果在时间片结束时进程还在运行，则CPU使用权将被剥夺并分配给另一个进程。如果进程在时间片结束前阻塞或结束，则CPU当即进行切换。
>
> 由于切换的时间很短（大概为5毫秒），切片时间也很短（一般为100毫秒），以人的反应结果就是感觉多个程序同时运行，且没有停顿（切换的时间和在别的切片上的时间

#### **3.1 两个线程**

一个负责从命令行接收消息，展示进程状态

另一个为守护进程，负责维护内部逻辑，并不断执行批处理指令



#### 3.2 逻辑主函数 start_manager()

打开exe文件同时创建父进程

每一个批处理指令会fork一个子进程用于执行该指令？

> 调度   是把CPU资源分配给进程
>
> 状态切换  io或timeout

#### 经典方式

- 从就绪队列调度
- 运行，持续时间为一个时间片or结束
  - [fork
  - [cpu, 5]  读取时间，判断时间片决定是否timeout
    - 批处理指令结束，转terminate
    - 还存在批处理指令，继续进就绪队列等待
  - [io, 10] 转到wait队列等待完成，
- 继续调度

#### 参考方式

- 循环
- 判断有无running进程，该进程有无批处理指令
  - 调用相关函数，执行批处理指令
- sleep一个时间片（离谱做法，违背原理）
-  **怎么转finish？ 对[cpu, 3]命令的处理？**
- 对记录的rs进行处理



## 四、可附加

### 性能评价

**非基本功能，先不做**

- cpu占用率
- 吞吐量
- 周转时间、等待时间

会额外增加一些变量记录公式中需要的参数



### 进程间通信

因为是模拟操作系统，接触不到底层，且python已经有信号量机制

故**无需此功能**



### 状态查看

- exec 执行文件
- ps进程状态
- rs资源状态

如何进行信息展示or可视化



## 改进的点

1. 每个进程维护一个子进程pid列表，kill父进程时同时会kill子进程
2. `ps`指令展示create_time变为exist_time 表示进程已运行多长时间
3. 变量pc相关逻辑能否删改优化？
4. timeout()处理的优化完善