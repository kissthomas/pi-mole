import logging
import pprint
import time

import RPi.GPIO as GPIO


class LCD1602(object):
    # Default GPIO to LCD mapping:
    RS = 17  # PIN 11
    E = 27   # PIN 13
    D4 = 22  # PIN 15
    D5 = 23  # PIN 16
    D6 = 24  # PIN 18
    D7 = 25  # PIN 22
    WIDTH = 16
    HEIGHT = 2
    ADDRS = [0x80, 0xC0, 0x94, 0xD4]

    def __init__(self, width=WIDTH, height=HEIGHT, rs=RS, e=E, d4=D4, d5=D5, d6=D6, d7=D7, line_addrs=None):
        self.logger = logging.getLogger('mole')
        self.logger.debug("Creating new LCD control with parameters: \n" + pprint.pformat(locals()))
        # Define some device constants
        if line_addrs is None:
            line_addrs = LCD1602.ADDRS
        self.LCD_CHR = True
        self.LCD_CMD = False
        # Timing constants
        self.E_PULSE = 0.0005
        self.E_DELAY = 0.0005
        self.LCD_WIDTH = width
        self.LCD_HEIGHT = height
        self.LCD_RS = rs
        self.LCD_E = e
        self.LCD_D4 = d4
        self.LCD_D5 = d5
        self.LCD_D6 = d6
        self.LCD_D7 = d7
        self.line_addrs = line_addrs
        self.cursorX = 0
        self.cursorY = 0
        self.buffer = [" ".ljust(width) for i in range(height)]

    def lcd_toggle_enable(self):
        # Toggle enable
        time.sleep(self.E_DELAY)
        GPIO.output(self.LCD_E, True)
        time.sleep(self.E_PULSE)
        GPIO.output(self.LCD_E, False)
        time.sleep(self.E_DELAY)

    def lcd_byte(self, bits, mode):
        # Send byte to data pins
        # bits = data
        # mode = True  for character
        #        False for command
        GPIO.output(self.LCD_RS, mode)  # RS
        # High bits
        GPIO.output(self.LCD_D4, False)
        GPIO.output(self.LCD_D5, False)
        GPIO.output(self.LCD_D6, False)
        GPIO.output(self.LCD_D7, False)
        if bits & 0x10 == 0x10:
            GPIO.output(self.LCD_D4, True)
        if bits & 0x20 == 0x20:
            GPIO.output(self.LCD_D5, True)
        if bits & 0x40 == 0x40:
            GPIO.output(self.LCD_D6, True)
        if bits & 0x80 == 0x80:
            GPIO.output(self.LCD_D7, True)
        # Toggle 'Enable' pin
        self.lcd_toggle_enable()
        # Low bits
        GPIO.output(self.LCD_D4, False)
        GPIO.output(self.LCD_D5, False)
        GPIO.output(self.LCD_D6, False)
        GPIO.output(self.LCD_D7, False)
        if bits & 0x01 == 0x01:
            GPIO.output(self.LCD_D4, True)
        if bits & 0x02 == 0x02:
            GPIO.output(self.LCD_D5, True)
        if bits & 0x04 == 0x04:
            GPIO.output(self.LCD_D6, True)
        if bits & 0x08 == 0x08:
            GPIO.output(self.LCD_D7, True)
        # Toggle 'Enable' pin
        self.lcd_toggle_enable()

    def init(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)  # Use BCM GPIO numbers
        GPIO.setup(self.LCD_E, GPIO.OUT)  # E
        GPIO.setup(self.LCD_RS, GPIO.OUT)  # RS
        GPIO.setup(self.LCD_D4, GPIO.OUT)  # DB4
        GPIO.setup(self.LCD_D5, GPIO.OUT)  # DB5
        GPIO.setup(self.LCD_D6, GPIO.OUT)  # DB6
        GPIO.setup(self.LCD_D7, GPIO.OUT)  # DB7
        # Initialise display
        self.lcd_byte(0x33, self.LCD_CMD)  # 110011 Initialise
        self.lcd_byte(0x32, self.LCD_CMD)  # 110010 Initialise
        self.lcd_byte(0x06, self.LCD_CMD)  # 000110 Cursor move direction
        self.lcd_byte(0x0C, self.LCD_CMD)  # 001100 Display On,Cursor Off, Blink Off
        self.lcd_byte(0x28, self.LCD_CMD)  # 101000 Data length, number of lines, font size
        self.lcd_byte(0x01, self.LCD_CMD)  # 000001 Clear display
        time.sleep(self.E_DELAY)

    def finish(self):
        self.lcd_byte(0x33, self.LCD_CMD)  # 110011 Initialise
        self.lcd_byte(0x32, self.LCD_CMD)  # 110010 Initialise
        self.lcd_byte(0x06, self.LCD_CMD)  # 000110 Cursor move direction
        self.lcd_byte(0x08, self.LCD_CMD)  # 001000 Display Off,Cursor Off, Blink Off
        self.lcd_byte(0x28, self.LCD_CMD)  # 101000 Data length, number of lines, font size
        self.lcd_byte(0x01, self.LCD_CMD)  # 000001 Clear display
        time.sleep(self.E_DELAY)
        GPIO.cleanup()

    def clear(self):
        self.lcd_byte(0x01, self.LCD_CMD)
        for j in range(0, self.LCD_HEIGHT):
            self.buffer[j] = " ".ljust(self.LCD_WIDTH)
        self.cursorX = 0
        self.cursorY = 0

    # Justification: 0 - no justification, 1 - left, 2 - center, 3 - right
    def print_line(self, message, line, justify=0):
        # Send string to display
        message = message[0:self.LCD_WIDTH]
        if justify == 3:
            message = message.rjust(self.LCD_WIDTH, " ")
            self.cursorX = self.LCD_WIDTH
        elif justify == 2:
            message = message.center(self.LCD_WIDTH, " ")
            self.cursorX = self.LCD_WIDTH
        else:
            if justify == 0:
                self.cursorX = len(message)
            else:
                self.cursorX = self.LCD_WIDTH
            message = message.ljust(self.LCD_WIDTH, " ")
        self.lcd_byte(self.line_addrs[line - 1], self.LCD_CMD)
        for i in range(self.LCD_WIDTH):
            self.lcd_byte(ord(message[i]), self.LCD_CHR)
        self.buffer[line - 1] = message

    def print(self, message, justify=0, newline=False):
        if not newline:
            self.print_line(message, self.cursorY, justify)
        else:
            if self.cursorY == self.LCD_HEIGHT:
                for j in range(0, self.LCD_HEIGHT - 1):
                    self.buffer[j] = self.buffer[j + 1]
                    self.print_line(self.buffer[j], j + 1)
            else:
                if self.cursorY < self.LCD_HEIGHT:
                    self.cursorY += 1
            self.print_line(message, self.cursorY, justify)

    def print_buffer(self, page):
        self.buffer = page
        for line in range(self.LCD_HEIGHT):
            self.lcd_byte(self.line_addrs[line], self.LCD_CMD)
            for i in range(self.LCD_WIDTH):
                self.lcd_byte(ord(self.buffer[line][i]), self.LCD_CHR)
