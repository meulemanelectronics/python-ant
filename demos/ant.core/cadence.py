"""
Use pygame to show speed and cadence data in a window using a big font
(only for combined speed/cadence sensor S&C profile - e.g. Garmin GSC10)

Based heavily on https://gist.github.com/ramunasd/a2e40cd13dd4cacf5685
"""
from __future__ import print_function

import sys
import time
from datetime import datetime

import pygame
import pygame.freetype
from pygame.locals import *

from ant.core import driver, node, event, message
from ant.core.constants import *

from config import *

def convertSB(raw):
    value = int(raw[1]) << 8
    value += int(raw[0])
    return value


class CadenceListener(event.EventCallback):
    prevCtime = 0
    prevWtime = 0
    prevWrevs = 0
    prevCrevs = 0
    wheelSpeed = 0
    crankSpeed = 0
    crankSpeedMax = 120
    initialized = False

    def getWheelSpeed(self):
        return self.wheelSpeed

    def process(self, msg):
        if not isinstance(msg, message.ChannelBroadcastDataMessage):
            return

        crankTime = convertSB(msg.payload[1:3])
        wheelTime = convertSB(msg.payload[5:7])

        crankRevolutions = convertSB(msg.payload[3:5]) 
        wheelRevolutions =  convertSB(msg.payload[7:9])

        if(not self.initialized):
            self.prevCtime = crankTime
            self.prevWtime = wheelTime
            self.prevCrevs = crankRevolutions
            self.prevWrevs = wheelRevolutions
            self.initialized = True
            return
        # handle wraparound
        if(crankTime < self.prevCtime):
            self.prevCtime = self.prevCtime - 65536
        if(wheelTime < self.prevWtime):
            self.prevWtime = self.prevWtime - 65536
        if(crankRevolutions < self.prevCrevs):
            self.prevCrevs = self.prevCrevs - 65536
        if(wheelRevolutions < self.prevWrevs):
            self.prevWrevs = self.prevWrevs - 65536

        if(crankTime > self.prevCtime):
            self.crankSpeed = 60 * 1024 * ((crankRevolutions - self.prevCrevs) /
                                           float(crankTime - self.prevCtime))
            print("crank", self.crankSpeed)
            self.prevCtime = crankTime
            self.prevCrevs = crankRevolutions

        if(wheelTime > self.prevWtime):
            revs = ((wheelRevolutions - self.prevWrevs) /
                    float(wheelTime - self.prevWtime))
            self.wheelSpeed = revs * 2205 * 3600 / 1024.0 
            print("wheel",
                  (float(wheelTime - self.prevWtime)),
                  self.wheelSpeed)
            self.prevWtime = wheelTime
            self.prevWrevs = wheelRevolutions



class Biscuit:
    listener = CadenceListener()
    def __init__(self):
        pygame.init()
        self.surface = pygame.display.set_mode()# (600,500))
        self.width = self.surface.get_width();
        self.height = self.surface.get_height();
        self.font = pygame.freetype.SysFont('Consolas', int(self.height/3))

    def on_update(self):
        self.surface.fill((10,20,10))
        self.font.render_to(self.surface,
                            (25,80),
                            "{: 5.1f} km/h".format(self.listener.wheelSpeed),
                            (0,255,0))
        self.font.render_to(self.surface,
                            (25,int(self.height/2)+10),
                            "{: 5.1f} rpm".format(self.listener.crankSpeed),
                            (0,255,0))
        now = datetime.now().strftime("%H:%M:%S")
        self.font.render_to(self.surface,
                            (200,int(3*self.height/5)+100),
                            now,
                            (0,255,0))
        pix = self.width *((self.listener.crankSpeed-40)/ self.listener.crankSpeedMax)
        pix = max(pix, 0)
        pygame.draw.rect(self.surface, (180,0,0), pygame.Rect(0,self.height/2-60, pix, 50))
        pygame.draw.rect(self.surface, (0,0,180), pygame.Rect(pix,self.height/2-60, 20, 50))
        pygame.display.flip()



NETKEY = b'\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

# Initialize
stick = driver.USB1Driver(SERIAL, log=LOG)# , debug=DEBUG)
antnode = node.Node(stick)
app = Biscuit()
antnode.registerEventListener(app.listener)
antnode.start(False)

# Set network key
network = node.Network(key=NETKEY, name='N:ANT+')
antnode.setNetworkKey(0, network)

# Get the first unused channel. Returns an instance of the node.Channel class.
channel = antnode.getFreeChannel()

# Initialize it as a receiving channel using our network key
channel.assign(network, CHANNEL_TYPE_TWOWAY_RECEIVE)

# https://infocenter.nordicsemi.com/index.jsp?topic=%2Fcom.nordic.infocenter.sdk5.v14.0.0%2Fant_examples_bicycle_spd_cad.html
# Set the channel ID to "0, 123, 0" for a speed receiver, "0, 122, 0" for a cadence receiver, or "0, 121, 0" for a combined receiver.
channel.setID(121, 0, 0)


# Listen forever and ever (not really, but for a long time)
channel.searchTimeout = TIMEOUT_NEVER

# set the radio frequency to 2457 MHz and the channel period to 8118 cycles (4,036 Hz) for a speed receiver, 8102 cycles (4,044 Hz) for a cadence receiver, or 8086 cycles (4,052 Hz) for a combined receiver.
channel.period = 8086

# And ANT frequency 57
channel.frequency = 57

running = True
try:
    # Time to go live
    channel.open()

    print("Listening for events...")
    while running:
        time.sleep(0.1)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYUP and event.key == pygame.K_q:
                running = False
        app.on_update()
    
finally:
    pygame.quit()
    # Shutdown channel
    channel.close()
    channel.unassign()

    # Shutdown
    antnode.stop()
