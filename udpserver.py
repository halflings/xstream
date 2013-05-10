import Queue
import SocketServer
import commonserver
import re
import socket
import threading
import time

#IMAGE FRAGMENTING
def fragmentImage(image, fragmentSize):
    """Fragments an image and returns a list containing those fragments"""
    return [image[i:min(i+fragmentSize, len(image))] for i in range(0, len(image), fragmentSize)]


def formatFragment(fragment, fragmentPosition, imgsize, imgid):
    """Returns a valid a query for the transmission of an image's fragment."""
    """BEWARE: fragmentPosition <-> position of the first byte of the fragment"""

    return "{}\r\n{}\r\n{}\r\n{}\r\n{}".format(imgid, imgsize, fragmentPosition, len(fragment), fragment)

class UDPThread(threading.Thread):
    UDP_LIFESPAN = 60

    def __init__(self, client_address, aTarget):
        self.client_address = client_address
        self.queries = Queue.Queue()
        self.dataSocket = None
        self.fragmentSize = 0
        self.listenPort = 0
        self.startTime = time.time()
        super(UDPThread, self).__init__(target=aTarget)
        self.daemon = True

    def queriesNumber(self):
        return self.queries.qsize()

    def getQuery(self):
        if not self.queries.empty():
            return self.queries.get()
        else:
            #Not supposed to get here, always test before
            return " "
    def pushQuery(self, query):
        self.queries.put(query)

    def extendLifespan(self):
        self.startTime = time.time()

    def timedOut(self):
        return (time.time() - self.startTime) > UDPThread.UDP_LIFESPAN

    def sendData(self, data):
        try:
            self.dataSocket.sendto(data, (self.client_address[0], self.listenPort) )
            return 1
        except:
            return 0

    def clear(self):
        self.queries.clear()

class MyUDPHandler(commonserver.CommonHandler):

    def handle(self):
        newConnection = True

        if self.client_address in self.server.threadsList:
            newConnection = not self.server.threadsList[self.client_address].isAlive()

        if newConnection:
            #If the client just connected or the client disconnected
            clientThread = UDPThread(self.client_address, self.processQuery)
            clientThread.start()

            self.server.threadsList[self.client_address] = clientThread
            self.server.newConnection()

        #Adding the request to the client's queries queue
        self.server.threadsList[self.client_address].pushQuery(self.request[0])

    def processQuery(self):
        clientThread = threading.current_thread()

        while clientThread.queriesNumber() == 0:
            #Sleeping instead of passing to avoid 100% CPU usage
            time.sleep(0.1)

        query = clientThread.getQuery()

        self.printLog("First UDP query received: {}".format(query))

        UDPQuery = re.search("GET ([0-9]+) \r\nLISTEN_PORT ([0-9]+) \r\nFRAGMENT_SIZE ([0-9]+) \r\n" , query)
        if UDPQuery:
            fluxID, clientThread.listenPort, clientThread.fragmentSize = int(UDPQuery.group(1)), int(UDPQuery.group(2)), int(UDPQuery.group(3))

            ########### A DIRTY BUGFIX TO MAKE THE SERVER WORK WITH THE PROVIDED CLIENTS ########
            clientThread.fragmentSize = clientThread.fragmentSize - 30                  ########
            ###################################################################################

            #Initializing the UDP data socket
            clientThread.dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            clientThread.dataSocket.connect((clientThread.client_address[0], clientThread.listenPort))

            if self.server.flux.protocol == "UDP_PUSH":
                self.printLog("Entering UDP Push mode. Client {}:{}".format(clientThread.client_address[0], clientThread.client_address[1]))
                return self.UDPPushMode(0)
            elif self.server.flux.protocol == "UDP_PULL":
                self.printLog("Entering UDP Pull mode. Client {}:{}".format(clientThread.client_address[0], clientThread.client_address[1]))
                return self.UDPPullMode(0)
            else:
                self.printLog("Wrong protocol for the requested flux - Not UDP." , "i")
                return 0

        else:
            self.printLog("The client {}:{} sent a first query ( {} ) that couldn't be interpreted".format(clientThread.client_address[0],
                clientThread.client_address[1], query), "i")
            return 0
            #ARBITRARY ERROR CODE
            #return self.sendToClient("400")

    def UDPPushMode(self, imgid):
        # Fetching the current (client) thread
        clientThread = threading.current_thread()

        # Used for delaying the image flux (to respect the framerate)
        delay = 1. / self.server.flux.ips

        #Waiting for start
        self.printLog("Entering WAIT FOR START loop")

        while True:

            query = clientThread.getQuery()
            if query == 0:
                self.printLog("Got empty query. Disconnecting.")
                return 0

            if re.search("START \r\n\r\n", query):
                self.printLog("Received START query")
                break

            time.sleep(0.0001)

        #Initializing timeSent to zero, to be sure we won't wait on the first iteration
        lastSent = 0
        while self.server.connected:

            # Fragmenting current image
            fragments = fragmentImage(self.server.flux.imageFiles[imgid], clientThread.fragmentSize)

            # Checking if the delay has passed, to respected the framerate
            if (time.time() - lastSent) < delay:
                time.sleep(delay - (time.time() - lastSent))

            # Sending the current image, and breaking the streaming loop if the client is not responding
            for fragmentid in range(len(fragments)):
                if not clientThread.sendData(formatFragment(fragments[fragmentid], fragmentid*clientThread.fragmentSize, len(self.server.flux.imageFiles[imgid]), imgid)):
                    self.printLog ("Couldn't send image {} to client {}. \n".format(imgid, clientThread.client_address[0], clientThread.listenPort) , "i")
                    return 0

            self.printLog("Sent image {} to client {}:{}.".format(imgid, clientThread.client_address[0], clientThread.listenPort))

            #Updating timeSent
            lastSent = time.time()

            #..Pausing
            while (clientThread.queriesNumber() != 0):
                query = clientThread.getQuery()

                if query == "PAUSE \r\n\r\n":
                    self.printLog ("Client {}:{} paused".format(clientThread.client_address[0], clientThread.client_address[1]))
                    return self.UDPPushMode(imgid)
                #.. or stopping the streaming
                if query == "END \r\n\r\n":
                    return 0

                if re.search("ALIVE {} \r\n".format(self.server.flux.id, clientThread.listenPort), query):
                    clientThread.extendLifespan()

            if clientThread.timedOut():
                    self.printLog("UDP Client {}:{} timed-out.".format(clientThread.client_address[0], clientThread.client_address[1]), "i")
                    break

            #Moving to the next image (starts from the beginning if the last image have been reached)
            imgid = (imgid + 1) % (len(self.server.flux.images))


        return 0

    def UDPPullMode(self, imgid):
        # Fetching the current (client) thread
        clientThread = threading.current_thread()

        while self.server.connected:

            while True:
                if clientThread.queriesNumber() > 0:
                    query = clientThread.getQuery()
                    getQuery = re.search("GET ([-]?[0-9]+) \r\n\r\n", query)
                    if getQuery:
                        if int(getQuery.group(1)) != -1:
                            imgid = int(getQuery.group(1))
                        break
                else:
                    time.sleep(0.00001)

            # Fragmenting current image
            fragments = fragmentImage(self.server.flux.imageFiles[imgid], clientThread.fragmentSize)


            # Sending the current image, and breaking the streaming loop if the client is not responding
            for fragmentid in range(len(fragments)):
                if not clientThread.sendData(formatFragment(fragments[fragmentid], fragmentid*clientThread.fragmentSize,
                    len(self.server.flux.imageFiles[imgid]), imgid)):
                    self.printLog ("Couldn't send image {} to client {}:{}. \n".format(imgid, clientThread.client_address[0],
                        clientThread.listenPort) , "i")
                    break

            self.server.notifySent(imgid)

            #..Processing received
            while (clientThread.queriesNumber() > 0):
                query = clientThread.getQuery()

                if query == "PAUSE \r\n\r\n":
                    self.printLog ("Client {}:{} paused".format(clientThread.client_address[0], clientThread.client_address[1]))
                    return self.UDPPushMode(imgid)
                #.. or stopping the streaming
                if query == "END \r\n\r\n":
                    self.printLog("Client {}:{} stopped".format(clientThread.client_address[0], clientThread.client_address[1]))
                    break

            #Moving to the current image to the next id (starts from the beginning if the last image have been reached)
            imgid = (imgid + 1) % (len(self.server.flux.images))

        return 0


class ThreadedUDPServer(commonserver.CommonServer, SocketServer.UDPServer):
    daemon_threads = True
    pass

