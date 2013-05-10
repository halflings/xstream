import commonserver
import socket
import time
import errno
from udpserver import fragmentImage, formatFragment


class MulticastServer(commonserver.CommonServer, socket.socket):

    def __init__(self, address, port, fragmentSize=512, family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, _sock=None):

        super(MulticastServer, self).__init__(family, type, proto, _sock)
        self.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        self.groupAddress = address
        self.groupPort = port
        self.fragmentSize = fragmentSize

    def serve_forever(self):

        delay = 1. / self.flux.ips
        imgid = 0
        lastSent = 0

        while self.connected:
            #self.printLog("Getting ready to fragment {}".format(imgid))
            fragments = fragmentImage(self.flux.imageFiles[imgid], self.fragmentSize)
            #self.printLog("Fragmented {} ! ".format(imgid))

            # Checking if the delay has passed, to respected the framerate
            if (time.time() - lastSent) < delay:
                time.sleep(delay - (time.time() - lastSent))

            # Sending the fragments
            for fragmentid in range(len(fragments)):
                formatedFragment = formatFragment(fragments[fragmentid], fragmentid * self.fragmentSize, len(self.flux.imageFiles[imgid]), imgid)
                try:
                    self.sendto(formatedFragment, (self.groupAddress, self.groupPort))
                except errno.EADDRNOTAVAIL:
                    self.printLog("Multicast address {}:{} is unreachable".format(self.flux.address, self.flux.port))
                #self.printLog("Sending fragment {} of image {}".format(fragmentid, imgid))
            lastSent = time.time()

            self.notifySent(imgid)


            imgid = (imgid + 1) % len(self.flux.images)

    def force_disconnect(self):
        self.connected = False
