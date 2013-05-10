# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uiserver.ui'
#
# Created: Wed Dec  5 10:19:03 2012
#      by: PyQt4 UI code generator 4.9.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
import datetime
import time
import server
import threading

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

# A "mediator" that transmits logs from the servers to the UI
class Logger(QtCore.QObject):
    logTrigger = QtCore.pyqtSignal(str, str)
    connectionTrigger = QtCore.pyqtSignal(int)
    def __init__(self):
        super(Logger,self).__init__()
    def send(self, string, mode):
        self.logTrigger.emit(string, mode)
    def updateConnections(self, number):
        self.connectionTrigger.emit(number)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(800, 600)

        #Initialization of the UI's widgets
        self.startStopGroup = QtGui.QGroupBox(Dialog)
        self.startStopGroup.setGeometry(QtCore.QRect(250, 530, 300, 41))
        self.startStopGroup.setTitle(_fromUtf8(""))
        self.startStopGroup.setAlignment(QtCore.Qt.AlignCenter)
        self.startStopGroup.setFlat(False)
        self.startStopGroup.setObjectName(_fromUtf8("startStopGroup"))
        self.startButton = QtGui.QPushButton(self.startStopGroup)
        self.startButton.setGeometry(QtCore.QRect(0, 0, 140, 40))
        self.startButton.setAutoRepeat(False)
        self.startButton.setObjectName(_fromUtf8("startButton"))
        self.stopButton = QtGui.QPushButton(self.startStopGroup)
        self.stopButton.setGeometry(QtCore.QRect(160, 0, 140, 40))
        self.stopButton.setObjectName(_fromUtf8("stopButton"))
        self.groupBox = QtGui.QGroupBox(Dialog)
        self.groupBox.setGeometry(QtCore.QRect(282, 490, 235, 29))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.ipEdit = QtGui.QLineEdit(self.groupBox)
        self.ipEdit.setGeometry(QtCore.QRect(0, 0, 150, 30))
        self.ipEdit.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.ipEdit.setObjectName(_fromUtf8("ipEdit"))
        self.portEdit = QtGui.QLineEdit(self.groupBox)
        self.portEdit.setGeometry(QtCore.QRect(156, 0, 80, 30))
        self.portEdit.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.portEdit.setObjectName(_fromUtf8("portEdit"))
        self.serverLog = QtGui.QTextEdit(Dialog)
        self.serverLog.setGeometry(QtCore.QRect(0, 0, 800, 480))
        self.serverLog.setObjectName(_fromUtf8("serverLog"))
        self.logMode = QtGui.QComboBox(Dialog)
        self.logMode.setGeometry(QtCore.QRect(577, 443, 110, 31))
        self.logMode.setObjectName(_fromUtf8("logMode"))
        self.logMode.addItem(_fromUtf8(""))
        self.logMode.addItem(_fromUtf8(""))
        self.clearLogButton = QtGui.QPushButton(Dialog)
        self.clearLogButton.setGeometry(QtCore.QRect(696, 443, 88, 31))
        self.clearLogButton.setObjectName(_fromUtf8("clearLogButton"))
        self.footerLabel = QtGui.QLabel(Dialog)
        self.footerLabel.setGeometry(QtCore.QRect(5, 575, 790, 20))
        self.footerLabel.setText(_fromUtf8(""))
        self.footerLabel.setObjectName(_fromUtf8("footerLabel"))
        self.setConnected(0)

        self.retranslateUi(Dialog)

        #Initializing the server to None
        self.server = None

        #Initializing the logger
        self.logger = Logger()
        #Connecting the server's logger signal to the printLog method
        self.logger.logTrigger.connect(self.printLog)
        self.logger.connectionTrigger.connect(self.setConnected)

        #Initializing the UI's signals
        self.clearLogButton.clicked.connect(self.clearLog)
        self.stopButton.clicked.connect(self.disconnectServer)
        self.startButton.clicked.connect(self.connectServer)

        #Opening the log file
        self.logFile = open("log.txt", "a+")
        logHeader = "\n"
        logHeader += "            ///////////////////////////\n"
        logHeader += "            Date : {} | Time: {}\n".format(datetime.date.today().strftime("%A %d. %B %Y"),time.strftime('%H:%M:%S', time.localtime()) )
        logHeader +="             ///////////////////////////\n\n"
        self.logFile.write(logHeader)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "XStream | Streaming GIFs FTW (╯°□°）╯︵ ┻━┻", None, QtGui.QApplication.UnicodeUTF8))
        Dialog.setWindowIcon(QtGui.QIcon(_fromUtf8("icon.png")))

        self.startButton.setText(QtGui.QApplication.translate("Dialog", "Start", None, QtGui.QApplication.UnicodeUTF8))
        self.stopButton.setText(QtGui.QApplication.translate("Dialog", "Stop", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox.setTitle(QtGui.QApplication.translate("Dialog", "GroupBox", None, QtGui.QApplication.UnicodeUTF8))
        self.ipEdit.setText(QtGui.QApplication.translate("Dialog", "127.0.0.1", None, QtGui.QApplication.UnicodeUTF8))
        self.portEdit.setText(QtGui.QApplication.translate("Dialog", "4242", None, QtGui.QApplication.UnicodeUTF8))
        self.clearLogButton.setText(QtGui.QApplication.translate("Dialog", "Clear", None, QtGui.QApplication.UnicodeUTF8))
        self.logMode.setItemText(0, QtGui.QApplication.translate("Dialog", "Important", None, QtGui.QApplication.UnicodeUTF8))
        self.logMode.setItemText(1, QtGui.QApplication.translate("Dialog", "Verbose", None, QtGui.QApplication.UnicodeUTF8))


    def connectServer(self):
        if (self.server is None):

            host = str(self.ipEdit.text())
            port = int(self.portEdit.text())

            try:
                self.server = server.MainServer((host, port), server.MyHTTPHandler)
                self.server.setup(self.logger)

                self.server.printLog( "Hooray ! Server succesfuly created at {}:{}".format(host, port), "i" )


                #Initializing a thread for the server -- this thread will then start one more thread for each connected client
                MainServer_thread = threading.Thread(target=self.server.serve_forever)
                MainServer_thread.daemon = True

                #Starting the server
                MainServer_thread.start()
            except:
                self.printLog("#ERROR: Address already in use. Try a different port." , "i")
            #except errno.EADDRNOTAVAIL:
            #    self.printLog("#ERROR: Address not available.", "i")
            #except socket.errno.EADDRINUSE:
            #    self.printLog("#ERROR: Address already in use. Try a different port." , "i")

        elif (self.server.connected):
            self.printLog( "The server is already connected at {}:{}".format(self.ipEdit.text(), self.portEdit.text()) , "i" )
        else:
            self.disconnectServer()
            self.server = None
            self.connectServer()

    def clearLog(self):
        self.logFile.write(self.serverLog.toPlainText())
        self.serverLog.clear()

    def disconnectServer(self):
        #Disconnect the server
        self.server.force_disconnect()

        #Add the current log and close the file
        self.logFile.write(self.serverLog.toPlainText())
        self.logFile.write("\n ~~~~~~ \n")
        self.logFile.close()
        #Closes the program
        QtCore.QCoreApplication.instance().quit()

    def setConnected(self, number):
        self.footerLabel.setText(_fromUtf8("Clients connected so far : {}".format(number)))

    def printLog(self, string, mode):
        if (mode == "i") or (self.logMode.currentIndex() == 1):
            self.serverLog.append(_fromUtf8(string + '\n' + '-'*20))


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    Dialog = QtGui.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())