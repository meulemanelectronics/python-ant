"""
Use pygame to show speed and cadence data in a window using a big font
(only for combined speed/cadence sensor S&C profile - e.g. Garmin GSC10)

Based heavily on https://gist.github.com/ramunasd/a2e40cd13dd4cacf5685
"""
from __future__ import print_function

import sys
import time

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
    lastC = 0
    lastW = 0
    wheelSpeed = 0
    crankSpeed = 0

    def getWheelSpeed(self):
        return self.wheelSpeed

    def process(self, msg):
        if not isinstance(msg, message.ChannelBroadcastDataMessage):
            return

        cadenceTime = convertSB(msg.payload[1:3])
        speedTime = convertSB(msg.payload[5:7])
        if cadenceTime == self.lastC and speedTime == self.lastW:
            return
        crankRevolutions = convertSB(msg.payload[3:5])
        wheelRevolutions =  convertSB(msg.payload[7:9])
        if speedTime > self.lastW:
            self.wheelSpeed = 3600 * 2105.0 /1024 / (speedTime - self.lastW)
        if cadenceTime > self.lastC:
            self.crankSpeed = 1024 * 60.0 / (cadenceTime - self.lastC) 
        self.lastW = speedTime
        self.lastC = cadenceTime



class Biscuit:
    listener = CadenceListener()
    def __init__(self):
        pygame.init()
        self.surface = pygame.display.set_mode((600,500))
        self.font = pygame.freetype.SysFont('Consolas', 90)

    def on_update(self):
        self.surface.fill((10,20,10))
        self.font.render_to(self.surface,
                            (25,80),
                            "{: 5.1f} km/h".format(self.listener.wheelSpeed),
                            (0,255,0))
        self.font.render_to(self.surface,
                            (25,300),
                            "{: 5.1f} rpm".format(self.listener.crankSpeed),
                            (0,255,0))
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

try:
    # Time to go live
    channel.open()

    print("Listening for events...")
    while True:
        time.sleep(0.1)
        app.on_update()

finally:
    # Shutdown channel
    channel.close()
    channel.unassign()

    # Shutdown
    antnode.stop()
