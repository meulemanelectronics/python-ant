# this is a large amount of guesswork, don't assume it's correct
# just because it's on github

import binascii
import random
import serial
import sys
import time


from ant.core import driver
from ant.core import event
from ant.core.constants import *
from ant.core.message import *

from config import *

NETKEY = b'\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

# Event callback
class MyCallback(event.EventCallback):
    def process(self, msg):
        print(msg)

# Initialize driver
stick = driver.USB1Driver("/dev/ttyUSB0", log=LOG, debug=DEBUG)
# stick = driver.USB2Driver(log=LOG, debug=DEBUG, idProduct=0x1008)
# stick = serial.Serial('/dev/ttyUSB0', 19200, rtscts=True,dsrdtr=True)
stick.open()

# Initialize event machine
evm = event.EventMachine(stick)
evm.registerCallback(MyCallback())
evm.start()

stick._write(bytes([0xa4,0x02,0x4d,0x00,0x54, 0xbf, 0x00, 0x00]))
time.sleep(1)
print(stick.read(255))

stick._write(bytes([0xa4,0x02,0x4d,0x00,0x3e, 0xd5, 0x00, 0x00]))
time.sleep(1)
print(stick.read(255))


# Reset
msg = SystemResetMessage()
# stick.write(msg + b'\x00\x00')
stick.write(msg)
stick.timeout = 0.2
time.sleep(1)
print(stick.read(255))
# if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
#     sys.exit()
time.sleep(1)

# Set network key
msg = NetworkKeyMessage(key=NETKEY)
stick.write(msg)

if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Now set the channel id for pairing with an ANT+ bike cadence/speed sensor
msg = ChannelIDMessage(device_type=121, device_number=0xdbdb, trans_type=0x1)
stick.write(msg)

if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# Initialize it as a sending channel using our network key
msg = ChannelAssignMessage(channelType = 0x10)
stick.write(msg)

if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

# And ANT frequency 57, of course
msg = ChannelFrequencyMessage(frequency=57)
stick.write(msg)

if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

msg = ChannelPeriodMessage(period = 8086)
stick.write(msg)

if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()


# Time to go live
msg = ChannelOpenMessage()
stick.write(msg)

if evm.waitForAck(msg) != RESPONSE_NO_ERROR:
    sys.exit()

def sandcdata(cadence_time, cadence_revs, speed_time, speed_revs):
    cadence_ms = 0xffff & (int(cadence_time * 1024))
    speed_ms = 0xffff & (int(speed_time * 1024))

    return [ cadence_ms % 256, cadence_ms >> 8, cadence_revs % 256, cadence_revs >> 8,
             speed_ms % 256, speed_ms >> 8, speed_revs % 256, speed_revs >> 8 ]

clock_time = 0.0
cadence_time = 0.0
speed_time = 0.0
cadence_revs  = 10
speed_revs  = 10
interval = 0.1
speed_period = 0.24 # seconds/wheel rev; 0.24 is somewhere around 30km/h
cadence_period = 1

def is_pedalling(cadence_time):
    return (cadence_time % 10.0) > 5.0

def is_speed_tick_time(clock_time, last_tick):
    return ((clock_time- last_tick) > speed_period)

def is_cadence_tick_time(clock_time, last_tick):
    return ((clock_time- last_tick) > cadence_period)


while True:
    clock_time= clock_time + interval
    speed_period = 0.24 + ( clock_time % 30)/30.0/2
    cadence_period = 1 - ( clock_time % 30)/30.0/2
    if (is_cadence_tick_time(clock_time, cadence_time)):
        print(clock_time, "pedal")
        cadence_time = clock_time
        cadence_revs = cadence_revs + 1
    if(is_speed_tick_time(clock_time, speed_time)):
        print(clock_time, "wheel")
        speed_time = clock_time
        speed_revs = speed_revs + 1
    data = bytes(sandcdata(cadence_time, int(cadence_revs),
                           speed_time, int(speed_revs)))
    msg = ChannelBroadcastDataMessage(data=data)
#    print(binascii.hexlify(data))
#    print("<< " + str(binascii.hexlify(msg.encode())))
    stick.write(msg)

    time.sleep(interval)


# Shutdown
msg = SystemResetMessage()
stick.write(msg)
time.sleep(1)

evm.stop()
stick.close()
