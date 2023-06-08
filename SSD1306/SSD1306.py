# /*****************************************************************************
# * | File        :   SSD1306.py
# * | Author      :   Waveshare team
# * | Function    :   SSD1306
# * | Info        :
# *----------------
# * | This version:   V1.0
# * | Date        :   2019-11-14
# * | Info        :   
# ******************************************************************************/
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
import pprint

from PIL import Image, ImageDraw, ImageFont
from smbus import SMBus


class SSD1306(object):
    WIDTH: int = 128
    HEIGHT: int = 32
    TEXT_WIDTH: int = 16
    TEXT_HEIGHT: int = 2
    FONT_SIZE: int = 15
    SMBUS_ADDR: int = 1
    ADDRESS: int = 0x3c

    def __init__(self, width=WIDTH, height=HEIGHT, smbus_addr=SMBUS_ADDR, addr=ADDRESS,
                 text_width=TEXT_WIDTH, text_height=TEXT_HEIGHT, font_file='', font_size=FONT_SIZE):
        self.logger = logging.getLogger('mole')
        self.logger.debug("Creating new OLED control with parameters: \n" + pprint.pformat(locals()))
        self.width = width
        self.height = height
        self.text_width = text_width
        self.text_height = text_height
        self.Column = width
        self.Page = int(height / 8)
        self.smbus_addr = smbus_addr
        self.addr = addr
        self.bus = SMBus(self.smbus_addr)
        self.image = Image.new('1', (self.width, self.height), "WHITE")
        self.draw = ImageDraw.Draw(self.image)
        self.font_size = font_size
        if font_file != '':
            self.font = ImageFont.truetype(font_file, font_size)
            self.font_size = font_size

    def send_command(self, cmd):
        self.bus.write_byte_data(self.addr, 0x00, cmd)

    def send_data(self, data):
        self.bus.write_byte_data(self.addr, 0x40, data)

    def close_bus(self):
        self.bus.close()

    def init(self):
        self.send_command(0xAE)
        self.send_command(0x40)  # set low column address
        self.send_command(0xB0)  # set high column address
        self.send_command(0xC8)  # not offset
        self.send_command(0x81)
        self.send_command(0xff)
        self.send_command(0xa1)
        self.send_command(0xa6)
        self.send_command(0xa8)
        self.send_command(0x1f)
        self.send_command(0xd3)
        self.send_command(0x00)
        self.send_command(0xd5)
        self.send_command(0xf0)
        self.send_command(0xd9)
        self.send_command(0x22)
        self.send_command(0xda)
        self.send_command(0x02)
        self.send_command(0xdb)
        self.send_command(0x49)
        self.send_command(0x8d)
        self.send_command(0x14)
        self.send_command(0xaf)

    def clear_buffer(self, color='WHITE'):
        self.image = Image.new('1', (self.width, self.height), color)
        self.draw = ImageDraw.Draw(self.image)

    def clear(self, color='WHITE'):
        self.clear_buffer(color)
        self.show()

    def get_buffer(self):
        buf = [0xff] * (self.Page * self.Column)
        image_monocolor = self.image.convert('1')
        imwidth, imheight = image_monocolor.size
        pixels = image_monocolor.load()
        if imwidth == self.width and imheight == self.height:
            # print ("Horizontal screen")
            for y in range(imheight):
                for x in range(imwidth):
                    # Set the bits for the column of pixels at the current position.
                    if pixels[x, y] == 0:
                        buf[x + int(y / 8) * self.width] &= ~(1 << (y % 8))
        elif imwidth == self.height and imheight == self.width:
            # print ("Vertical screen")
            for y in range(imheight):
                for x in range(imwidth):
                    new_x = y
                    new_y = self.height - x - 1
                    if pixels[x, y] == 0:
                        buf[(new_x + int(new_y / 8) * self.width)] &= ~(1 << (y % 8))
        for x in range(self.Page * self.Column):
            buf[x] = ~buf[x]
        return buf

    def show(self):
        buffer = self.get_buffer()
        for i in range(0, self.Page):
            self.send_command(0xB0 + i)  # set page address
            self.send_command(0x00)  # set low column address
            self.send_command(0x10)  # set high column address
            # write data #
            for j in range(0, self.Column):
                self.send_data(buffer[j + self.width * i])

    def print_buffer(self, page):
        self.clear_buffer()
        line_number = 0
        for line in page:
            self.draw.text((0, line_number * self.font_size), line, font=self.font, fill=0)
            line_number += 1
            if line_number >= self.height:
                break
        self.show()
