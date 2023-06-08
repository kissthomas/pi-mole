import logging
import pprint
import threading
import time

from PoEHAT import FAN


class FANCONTROL(object):
    TEMP_MIN: int = 50
    TEMP_MAX: int = 55
    THERMAL: str = '/sys/class/thermal/thermal_zone0/temp'

    def __init__(self, fan, interval=5, temp_min=TEMP_MIN, temp_max=TEMP_MAX, thermal=THERMAL):
        self.logger = logging.getLogger('mole')
        self.logger.debug("Creating new FANCONTROL control with parameters: \n" + pprint.pformat(locals()))
        self.interval = interval
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.thermal = thermal
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True  # Daemonize thread
        self.fan: FAN = fan
        self.running = False

    def start(self):
        self.running = True
        self.thread.start()  # Start the execution

    def stop(self):
        self.running = False

    def temp(self):
        with open(self.thermal, 'rt') as f:
            temp = int(f.read()) / 1000.0
        f.close()
        return temp

    def run(self):
        while self.running:
            temp = self.temp()
            if temp > self.temp_max and not self.fan.running:
                self.logger.info('Turning fan ON. Temp: ' + str(temp))
                self.fan.on()
            if temp < self.temp_min and self.fan.running:
                self.logger.info('Turning fan OFF. Temp: ' + str(temp))
                self.fan.off()
            time.sleep(self.interval)
