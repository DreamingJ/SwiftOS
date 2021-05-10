import datetime
import subprocess
import logging
import os
import signal
import sys
import traceback
import sqlite3

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebSockets import *

#from file_manager import FileManager

class Window(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowMinMaxButtonsHint|Qt.WindowCloseButtonHint)

        self.setWindowTitle('LocalGUI')      

        self.usernameLine = QLineEdit('buptosuser')
        self.passwordLine = QLineEdit('123456')
        self.cautionLine = QLineEdit('welcome to swiftOS')
        self.passwordLine.setEchoMode(QLineEdit.Password)


        self.logBtn = QPushButton('Login')
        self.regBtn = QPushButton('Register')
        self.logBtn.clicked.connect(self.startClicked)
        self.regBtn.clicked.connect(self.regClicked)

        formLayout = QFormLayout()     
        formLayout.addRow(QLabel('Username:'), self.usernameLine)
        formLayout.addRow(QLabel('Password:'), self.passwordLine)
        formLayout.addRow(QLabel(), self.cautionLine)
        formLayout.addRow(QLabel(''), self.logBtn)
        formLayout.addRow(QLabel(''), self.regBtn)
      
        self.setLayout(formLayout)
        self.resize(300, 300)

        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.bytesWritten.connect(self.processBytesWritten)
        self.process.errorOccurred.connect(self.processErrorOccurred)
        self.process.finished.connect(self.processFinished)
        self.process.started.connect(self.processStarted)
        self.process.stateChanged.connect(self.processStateChanged)
        self.process.readyReadStandardOutput.connect(self.processReadyRead)

    def processBytesWritten(self, byteCount):
        log.debug(f'bytes={byteCount}')
    
    def processErrorOccurred(self, error):
        log.debug(f'err={error}')

    def processFinished(self):
        process = self.sender()
        log.debug(f'pid={process.processId()}')
        self.logBtn.setText('Start')
        self.processIdLine.setText('')

    def processReadyRead(self):
        data = self.process.readAll()
        try:
            msg = data.data().decode("utf8","ignore").strip()
            log.debug(f'msg={msg}')
        except Exception as exc:
            log.error(f'{traceback.format_exc()}')
            exit(1)

    def processStarted(self):
        process = self.sender()
        processId = process.processId()
        log.debug(f'pid={processId}')
        self.logBtn.setText('Stop')
        self.processIdLine.setText(str(processId))

    
    def processStateChanged(self):
        process = self.sender()
        log.debug(f'pid={process.processId()} state={process.state()}')

    def regClicked(self):
        btn = self.sender()
        text = btn.text().lower()

        username = self.usernameLine.text()
        password = self.passwordLine.text()

        path = os.getcwd() 

        conn = sqlite3.connect(path + os.sep + "SwiftOs" + "database.db") 
        conn.isolation_level = None #这个就是事务隔离级别，默认是需要自己commit才能修改数据库，置为None则自动每次修改都提交,否则为""
        # 下面就是创建一个表
        conn.execute("create table if not exists User (Username VARCHAR(20) PRIMARY KEY, Password VARCHAR(20))") 
        # 插入数据
        conn.execute("insert into User(Username,Password) values (?,?)",(username, password))
        conn.commit()
        conn.close()

        os.makedirs(os.getcwd() + os.sep + "SwiftOS_files" +  os.sep + username)
        os.system("python kernel.py %s" % (username) )
        

        

    def startClicked(self):
        btn = self.sender()
        text = btn.text().lower()
        
           
        username = self.usernameLine.text()
        password = self.passwordLine.text()

        path = os.getcwd()
        conn = sqlite3.connect(path + os.sep + "SwiftOs" + "database.db") 

        conn.isolation_level = None #这个就是事务隔离级别，默认是需要自己commit才能修改数据库，置为None则自动每次修改都提交,否则为""
        # 下面就是创建一个表
        conn.execute("create table if not exists User (Username VARCHAR(20) PRIMARY KEY, Password VARCHAR(20))") 
        # 插入数据
        conn.execute("insert into User(Username,Password) values ('wxc', 'wxc123')")
        conn.execute("insert into User(Username,Password) values ('jmj', 'jmj123')")
        # 如果隔离级别不是自动提交就需要手动执行commit
        conn.commit()
        # 获取到游标对象
        cur = conn.cursor()
        # 用游标来查询就可以获取到结果
        finds = cur.execute("SELECT Password FROM User WHERE Username=?", (username,))
      
        conn.close()
        if finds[0] == password:
            os.system("python kernel.py %s" % (username) )
        else:
            self.cautionLine.setText("password error!")   
         
            #pythonExec = os.path.basename(sys.executable)

            ##cmd1 = 'e:/Programs/path/OSenv/Scripts/python.exe E:/Programs/swiftos/SwiftOS/kernel.py'
            #p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            #os.system("python kernel.py %s" % (username) )

            #subprocess.call('start /wait python kernel.py', shell=True)
            #cmdLine = f'{pythonExec} kernel.py local  -u {username} -w {password} '
            #log.debug(f'cmd={cmdLine}')
            #self.process.start(cmdLine)
    

    def websocketConnected(self):
        self.websocket.sendTextMessage('secret')

    def websocketDisconnected(self):
        self.process.kill()

    def websocketMsgRcvd(self, msg):
        log.debug(f'msg={msg}')
        
        nowTime = QDateTime.currentDateTime().toString('hh:mm:ss')
        
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
 
    logFmt = logging.Formatter('%(asctime)s %(lineno)-3d %(levelname)7s %(funcName)-26s %(message)s')
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.DEBUG)
    consoleHandler.setFormatter(logFmt)
    log = logging.getLogger(__file__)
    log.addHandler(consoleHandler)
    log.setLevel(logging.DEBUG)

    app = QApplication(sys.argv)
   
    app.setStyle('Windows')
    win = Window()
    win.show()
    sys.exit(app.exec_())
