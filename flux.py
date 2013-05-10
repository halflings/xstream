class Flux:

    def __init__(self, aId, aName, aType, aAddress, aPort, aProtocole, aIPS):
        self.id = int(aId)
        self.name = aName
        self.type = aType
        self.address = aAddress
        self.port = int(aPort)
        self.protocol = aProtocole
        self.ips = float(aIPS)
        self.images = []
        self.imageFiles = []

    def addImages(self, aImages):
        self.images += aImages
        self.loadImages()

    def loadImages(self):
        for imagePath in self.images:
            try:
                imgfile = open(imagePath, 'rb')
                self.imageFiles.append(imgfile.read())
                imgfile.close()
            except IOError:
                print "Image {} couldn't be opened \n".format(imagePath)

    #def openImage(self, imgIndex = 0):
    #    if self.currentImage is None:
    #        try:
    #            self.currentImage = open(self.images[imgIndex])
    #            self.currentID = imgIndex
    #            return self.currentImage
    #        except IOError:
    #            print "Image {} couldn't be opened \n".format(self.images[imgIndex])
    #            return 0
    #    
    #def nextImage(self):
    #    if (self.currentID == len(self.images) - 1):
    #        print "Current image of ID: {} is the last image.".format(self.currentID)
    #        return 0
    #    else:
    #        #self.currentImage.close()
    #        self.openImage(self.currentID + 1)
    #        return 1
        
    def getParameters(self):
        return [ self.id, self.name, self.type, self.address, self.protocol, self.ips, self.images ] #, self.currentImage ]