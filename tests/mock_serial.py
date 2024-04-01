"""
Mock serial is used to handle and create virtual serial ports using pyserial's loopback interface capability

"""

from time import sleep, time_ns

from serial.urlhandler.protocol_loop import Serial as LoopSerial


class MockPort:
    pass
