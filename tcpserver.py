import SocketServer
import threading
import socket
import re
import time
import commonserver

class MyTCPHandler(commonserver.CommonHandler, SocketServer.BaseRequestHandler):

    def handle(self):
        self.data = ""
        self.server.clientsCount += 1
        cur_thread = threading.current_thread()
        self.printLog ( "New client {}:{} connected to the flux.".format(self.client_address[0],self.client_address[1], self.server.clientsCount))
        self.printLog( "Current server thread : {}".format(cur_thread.name) )
        is_Sent = 1
        while is_Sent:
            self.receiveData()
            self.server.printLog("Client {}:{} sent : {}".format(self.client_address[0],self.client_address[1], self.data))
            is_Sent = self.processQuery(self.data)

        self.server.clientsCount = max(self.server.clientsCount-1, 0)

        self.server.printLog("TCP connection with {}:{} ended.".format(self.client_address[0],self.client_address[1], self.server.clientsCount), "i")

    def sendImageFormat(self, image, imageID):
        size = len(image)
        return "{}\r\n{}\r\n{}".format(imageID, size, image)

    def processQuery(self, query):

        TCPQuery = re.search("GET ([0-9]+) \r\nLISTEN_PORT ([0-9]+) \r\n\r\n" , query)

        if TCPQuery:
            fluxID = int(TCPQuery.group(1))
            listenPort = int(TCPQuery.group(2))
            self.printLog ( "Client wants flux : {} ; In port : {}".format(fluxID, listenPort) )

            #Initializing control thread
            self.control_thread = threading.Thread(target = self.receiveData)
            self.control_thread.daemon = True
            self.control_thread.start()

            #Initializing TCP data socket
            self.dataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.dataSocket.connect((self.client_address[0], listenPort))

            if self.server.flux.protocol == "TCP_PUSH":
                return self.TCPPushMode(0)
            elif self.server.flux.protocol == "TCP_PULL":
                return self.TCPPullMode(0)
            else:
                self.printLog ( "Wrong protocol for the requested flux - Not TCP.", "i" )
                return 0
            # END OF "if TCPQUERY"

        else:
            self.printLog ( "The client sent a query '{}' that couldn't be interpreted".format(query), "i" )
            #ARBITRARY ERROR CODE

    def sendToClient(self, data):
        try:
            self.request.sendall(data)
            self.server.printLog("Server sent query : {}".format(data))
            return 1
        except:
            self.server.printLog("Couldn't transmit query. Shutting down.", "i")
            return 0

    def sendData(self, data):
        try:
            self.dataSocket.sendall(data)
            return 1
        except:
            self.server.printLog("Couldn't transmit data to {}:{}. Shutting down.".format(self.client_address[0], self.client_address[1]), "i")
            return 0

    def receiveData(self):
        try:
            self.data = self.request.recv(1024)
            return 1
        except:
            return 0
    def TCPPushMode(self, imgid):

        delay = 1./self.server.flux.ips

        #Waiting for START
        while True:
            if re.search("START \r\n\r\n", self.data):
                #Flushing data
                self.data = " "
                break
            #Waiting for the control thread to die -> To get a new query
            self.control_thread.join()

            if self.data == 0:
                return 0

            #Restarting the control thread
            self.control_thread = threading.Thread(target = self.receiveData)
            self.control_thread.daemon = True
            self.control_thread.start()


         #Initializing timeSent to zero, to be sure we won't wait on the first iteration
        lastSent = 0
        #Sending images to client
        while self.server.connected:
            # Checking if the delay has passed, to respected the framerate
            if (time.time() - lastSent) < delay:
                time.sleep(delay - (time.time() - lastSent))

            #Sending the current image, and breaking the streaming loop if the client is not responding
            if not self.sendData(self.sendImageFormat(self.server.flux.imageFiles[imgid], imgid)):
                self.printLog ( "Couldn't send image {} to client {}. \n".format(imgid, self.client_address[0],self.client_address[1]) , "i" )
                return 0
            else:
                self.server.notifySent(imgid)
            # Getting the sending time, to respect the flux's framerate
            lastSent = time.time()

            #..Pausing
            if self.data == "PAUSE \r\n\r\n":
                self.printLog ( "Client {}:{} paused".format(self.client_address[0],self.client_address[1]) )
                self.data = " "
                return self.TCPPushMode(imgid)
            #.. or stopping the streaming
            if self.data == "END \r\n\r\n":
                return 0

            #Moving to the next image (starts from the beginning if the last image have been reached)
            imgid = (imgid + 1) % (len(self.server.flux.images))


            if not self.control_thread.isAlive():
                self.control_thread = threading.Thread(target = self.receiveData)
                self.control_thread.daemon = True
                self.control_thread.start()
            #Else: Keep calm and stream.

        return 0

    def TCPPullMode(self, imgid):
        imgid = imgid -1

        #Sending images to client
        while self.server.connected:

            #Waiting for the control thread to die (-> get a new query)
            self.control_thread.join()
            #Restarting the control thread
            self.control_thread = threading.Thread(target = self.receiveData)
            self.control_thread.daemon = True
            self.control_thread.start()

            #Processing the received query
            GETQuery = re.search("GET ([-]?[1-9]+) \r\n\r\n", self.data)
            if GETQuery:
                if int(GETQuery.group(1)) == -1:
                    # If IMG_ID is -1, we send the next image
                    imgid = (imgid + 1) % len(self.server.flux.images)
                else:
                    imgid = int(GETQuery.group(1))

                #Sending the current image, and breaking the streaming if the client is not responding
                if not self.sendData(self.sendImageFormat(self.server.flux.imageFiles[imgid], imgid)):
                    self.printLog( "Couldn't send image {} to client. \n".format(imgid))
                    return 0
                else:
                    self.server.notifySent(imgid)


            #..Pausing
            if self.data == "PAUSE \r\n\r\n":
                self.printLog(  "Client {}:{} paused".format(self.client_address[0],self.client_address[1]) )
                return self.TCPPushMode(imgid)
            #.. or stopping the streaming
            elif self.data == "END \r\n\r\n":
                return 0
            #Else: Keep calm and stream again

class ThreadedTCPServer(commonserver.CommonServer, SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    daemon_threads = True
    pass