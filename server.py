import tcpserver
import udpserver
import multicast
import SocketServer
import threading
import flux
import commonserver

FLUXLIST_PATH = "startup.txt"

class MainServer(commonserver.CommonServer, SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def setup(self, logger):
        self.connected = True
        self.clientsCount = 0
        self.logger = logger

        #Loading the flux list
        self.fluxList = []
        fluxFile = open(FLUXLIST_PATH)
        for line in fluxFile:
            self.loadFlux(line.rstrip("\r\n"))

        #Creatings the sockets
        self.servers = []
        for curFlux in self.fluxList:
            if curFlux != 0:
                if curFlux.protocol == "TCP_PUSH" or curFlux.protocol == "TCP_PULL":
                    #self.printLog( "FLUX - TCP SOCKET CREATION => {}:{} \n FLUX ID IS : {}".format(flux.address, flux.port, flux.id) )
                    server = tcpserver.ThreadedTCPServer((curFlux.address, int(curFlux.port)), tcpserver.MyTCPHandler)
                elif curFlux.protocol == "UDP_PULL" or curFlux.protocol == "UDP_PUSH":
                    #self.printLog( "FLUX - UDP SOCKET CREATION => {}:{} \n FLUX ID IS : {}".format(flux.address, flux.port, flux.id) )
                    server = udpserver.ThreadedUDPServer((curFlux.address, int(curFlux.port)), udpserver.MyUDPHandler)
                elif curFlux.protocol == "MCAST_PUSH":
                    #self.printLog( "FLUX - UDP MULTICAST SOCKET CREATION => {}:{} \n FLUX ID IS : {}".format(flux.address, flux.port, flux.id) )
                    server = multicast.MulticastServer(address = curFlux.address, port = curFlux.port)

                server.setup(curFlux, self.logger)
                server_thread = threading.Thread(target=server.serve_forever)


                # Exit the server thread when the main thread terminates
                server_thread.daemon = True
                server_thread.start()

                self.servers.append(server)


        self.catalogue = self.generateCatalogue()

        self.printLog("The flux have been imported and the catalogue generated !", "i")

    def loadFlux(self, fluxPath):
        fluxFile = open(fluxPath)
        fluxParams = []
        for i in range(7):
            line = fluxFile.readline()
            lineElems = line.split(' ')
            fluxParams.append(lineElems[1].rstrip("\r\n"))
        images = []
        for line in fluxFile:
            images.append(line.rstrip("\r\n"))

        fluxFile.close()

        cur_flux = flux.Flux(*fluxParams)

        if len(images)>0:
            cur_flux.addImages(images)
            self.fluxList.append(cur_flux)
        else:
            self.fluxList.append(0)

    def generateCatalogue(self):
        catalogue = "ServerAddress: {} \r\n".format(self.server_address[0])
        catalogue += "ServerPort: {} \r\n".format(self.server_address[1])
        for flux in self.fluxList:
            if flux != 0:
                catalogue += "Object ID={} name={} type={} address={} port={} protocol={} ips={} \r\n".format(flux.id, flux.name, flux.type,\
                                                                                                              flux.address, flux.port, flux.protocol, flux.ips)
        catalogue += "\r\n"

        return catalogue

    def force_disconnect(self):
        for server in self.servers:
            server.force_disconnect()

        self.server_close()
        self.connected = False

    def newConnection(self):
        self.clientsCount += 1
        self.logger.updateConnections(self.clientsCount)

    def lostConnection(self):
        #self.clientsCount -= 1
        self.logger.updateConnections(self.clientsCount)

class MyHTTPHandler(commonserver.CommonHandler):
    daemon_threads = True

    def handle(self):

        cur_thread = threading.current_thread()
        self.printLog( "New client connected to the server. Address : {}:{}".format(self.client_address[0],self.client_address[1]), "i" )
        self.printLog( "Current server thread : {}".format(cur_thread.name) )
        self.server.newConnection()


        while self.server.connected:
            try:
                self.data = self.request.recv(1024)
                answer = self.HTTPGetResponse(self.server.catalogue)
                self.request.sendall(answer)
                self.printLog("MainServer sent catalogue to {}:{} ".format(self.client_address[0], self.client_address[1]))

            except:
                self.printLog("Couldn't transmit data to {}:{}. Shutting down.".format(self.client_address[0], self.client_address[1]) , "i" )
                #self.server.shutdown()
                break

        self.printLog("MainServer connection with {}:{} ended.".format(self.client_address[0],self.client_address[1]) , "i" )
        self.server.lostConnection()

    def HTTPGetResponse(self, content):

        header = "HTTP/1.1 200 OK\r\n"
        header += "Host : {}:{}\r\n".format(self.server.server_address[0], self.server.server_address[1])
        header += "Date : Tue, 20 Nov 2012 13:37:42 GMT Server : Microsoft-IIS/2.0\r\n"
        header += "Content-Type : text/HTML\r\n"
        header += "Content-Length : {}\r\n".format(str(len(content)))
        header += "Last-Modified : Fri, 14 Jan 2000 11:11:11 GMT\r\n\r\n"

        return header + content