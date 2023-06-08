import logging
import pprint
import threading
import time

import RPi.GPIO as GPIO


class BUZZER(object):
    # Default GPIO to LCD mapping:
    B: int = 21  # PIN 40

    def __init__(self, buzzer=B):
        self.logger = logging.getLogger('mole')
        self.logger.debug("Creating new BUZZER control with parameters: \n" + pprint.pformat(locals()))
        self.BUZZER = buzzer

    def init(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)  # Use BCM GPIO numbers
        GPIO.setup(self.BUZZER, GPIO.OUT)

    @staticmethod
    def finish():
        GPIO.cleanup()

    def on(self):
        GPIO.output(self.BUZZER, True)

    def off(self):
        GPIO.output(self.BUZZER, False)

    def beep(self, duration):
        self.on()
        time.sleep(duration)
        self.off()

    def background_beep(self, duration):
        thread = threading.Thread(target=self.beep, args=(duration,))
        thread.start()
