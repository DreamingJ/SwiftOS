import datetime
import subprocess
import logging
import os
import signal
import sys
import traceback
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebSockets import *

class Window(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowMinMaxButtonsHint|Qt.WindowCloseButtonHint)

        self.setWindowTitle('LocalGUI')      

        self.usernameLine = QLineEdit('buptosuser')
        self.passwordLine = QLineEdit('123456')
        self.passwordLine.setEchoMode(QLineEdit.Password)


        self.startBtn = QPushButton('Start')
        self.startBtn.clicked.connect(self.startClicked)

        self.sendBandwidthLine = QLabel()
        self.recvBandwidthLine = QLabel()

        formLayout = QFormLayout()     
        formLayout.addRow(QLabel('Username:'), self.usernameLine)
        formLayout.addRow(QLabel('Password:'), self.passwordLine)
        formLayout.addRow(QLabel(''), self.startBtn)
      
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
        self.startBtn.setText('Start')
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
        self.startBtn.setText('Stop')
        self.processIdLine.setText(str(processId))

    
    def processStateChanged(self):
        process = self.sender()
        log.debug(f'pid={process.processId()} state={process.state()}')

    def startClicked(self):
        btn = self.sender()
        text = btn.text().lower()
        if text.startswith('start'):
           
            username = self.usernameLine.text()
            password = self.passwordLine.text()
         
            pythonExec = os.path.basename(sys.executable)

            cmd = 'python kernel.py'
            cmd1 = 'e:/Programs/path/OSenv/Scripts/python.exe E:/Programs/swiftos/SwiftOS/kernel.py'
            #p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            os.system("python kernel.py %s" % (username) )

            #subprocess.call('start /wait python kernel.py', shell=True)
            #cmdLine = f'{pythonExec} kernel.py local  -u {username} -w {password} '
            #log.debug(f'cmd={cmdLine}')
            #self.process.start(cmdLine)
        else:
            self.process.kill()

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
    # app.setQuitOnLastWindowClosed(False)
    app.setStyle('Windows')
    win = Window()
    win.show()
    sys.exit(app.exec_())
