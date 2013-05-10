import SocketServer
import time

class CommonHandler(SocketServer.BaseRequestHandler, object):
    def __int__(self, request, client_address, server):
        super(CommonHandler).__init__(request, client_address, server)
        self.transferedData = 0

    def printLog(self, string, mode = "v"):
        self.server.printLog(string, mode)

class CommonServer:
    allow_reuse_address = True

    def setup(self, flux, logger):
        self.flux = flux
        self.logger = logger
        self.connected = True
        self.clientsCount = 0
        self.threadsList = dict()

    def printLog(self, message, mode ="v"):
        try:
            message = "#{}(id={}) : {}".format(self.flux.protocol, self.flux.id, message)
        except:
            message = "#MainServer : {}".format(message)

        currentTime = time.strftime('%H:%M:%S', time.localtime())
        message = "[{}] {}".format(currentTime, message)

        self.logger.send(message, mode)

    def serve_forever(self):
        while self.connected:
            self.handle_request()

    def force_disconnect(self):
        self.connected = self
        #False.shutdown()
        self.server_close()

    def newConnection(self):
        self.clientsCount += 1
        self.printLog("New viewer on this flux | Total number of viewers : {}".format(self.clientsCount))

    def lostConnection(self):
        self.clientsCount -= 1

    def notifySent(self, imgid):
        done = int(50*(imgid + 1.)/len(self.flux.images))
        self.printLog("Sent image {}/{} in flux #{} \n|#".format(imgid,
            len(self.flux.images)-1, self.flux.id) + "#"*done + " "*(50-done) + "|")
