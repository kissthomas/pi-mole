import logging
import pprint

import smbus


class FAN(object):
    SMBUS: int = 1
    ADDRESS: int = 0x20

    def __init__(self, smbus_addr=SMBUS, address=ADDRESS):
        self.logger = logging.getLogger('mole')
        self.logger.debug("Creating new FAN control with parameters: \n" + pprint.pformat(locals()))
        self.smbus_addr = smbus_addr
        self.address = address
        self.i2c = smbus.SMBus(self.smbus_addr)
        self.running = False

    def off(self):
        self.i2c.write_byte(self.address, 0x01 | self.i2c.read_byte(self.address))
        self.running = False

    def on(self):
        self.i2c.write_byte(self.address, 0xFE & self.i2c.read_byte(self.address))
        self.running = True
