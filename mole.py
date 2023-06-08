#!/usr/bin/python

import configparser
import getopt
import logging
import logging.handlers
import os
import pprint
import signal
import sys
import threading
import time
from inspect import getmembers

import netifaces
import pyshark

from LCD1602 import LCD1602
from PoEHAT import BUZZER
from PoEHAT import FAN
from PoEHAT import FANCONTROL
from SSD1306 import SSD1306
from pager import Pager

DIR_PATH: str = os.path.dirname(os.path.abspath(__file__))
HELP: str = DIR_PATH + '/mole.py -h | -f <device_filter> -i <cap_interface>'

# Define CDP settings
CDP_FILTER: str = \
    '(ether proto 0x88cc) or (ether host 01:00:0c:cc:cc:cc and ether[16:4] = 0x0300000C and ether[20:2] == 0x2000)'
DEFAULT_FILTER: int = 0x00000008
# Capabilities: 0x00000???
# .... .... ...1 = Router
# .... .... ..1. = Transparent Bridge
# .... .... .1.. = Source Route Bridge
# .... .... 1... = Switch
# .... ...1 .... = Host
# .... ..1. .... = IGMP capable
# .... .1.. .... = Repeater
# .... 1... .... = VoIP Phone
# ...1 .... .... = Remotely Managed device
# ..1. .... .... = CVTA/STP Dispute Resolution/Cisco VT Camera
# .1.. .... .... = Two Port Mac Relay

capability: int = DEFAULT_FILTER
cap_interface: str = 'eth0'
config: configparser = configparser.ConfigParser()
logger: logging = logging.getLogger('mole')
log_file: str

has_buzzer: bool
has_fan: bool
has_fan_control: bool
has_oled: bool
has_lcd: bool
lcd: LCD1602
oled: SSD1306
buzzer: BUZZER
fan: FAN
fancontrol: FANCONTROL
pager: Pager
pager_running: bool = False
ip_interface: str = 'br0'
ip: str = '0.0.0.0'


def debug_dump(data):
    global log_file
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    with open(log_file, "a") as file_object:
        file_object.write(current_time + ": \n")
        file_object.write(data)
        file_object.write("\n----------------------------------------------------------------------------\n")
        file_object.close()


def short_ifname(line):
    line = line.replace('TenGigabitEthernet', 'Te')
    line = line.replace('GigabitEthernet', 'Gi')
    line = line.replace('FastEthernet', 'Fas')
    line = line.replace('Ethernet', 'Eth')
    line = line.replace('Loopback', 'Lo')
    line = line.replace('bridge', 'Br')
    line = line.replace('ether', 'Eth')
    return line


def print_packet_info(packet):
    global has_buzzer, has_fan, has_fan_control, has_oled, has_lcd, lcd, logger, log_file, oled, buzzer, capability, pager
    logger.debug('Got NEW PACKET! :)')
    if has_buzzer:
        buzzer.background_beep(0.1)

    if hasattr(packet, 'cdp'):
        logger.debug('New packet is CDP.')
        capabilities = int(packet.cdp.Capabilities, base=16)
        if capabilities & capability == capability:
            ip = ''
            if hasattr(packet.cdp, 'nrgyz_ip_address'):
                ip = packet.cdp.nrgyz_ip_address
            logger.info(
                'Just arrived: CDP ' + packet.cdp.DeviceID + " (" + ip + "), " + packet.cdp.PortID + ", " + packet.cdp.Capabilities)
            if logger.getEffectiveLevel() == logging.DEBUG:
                debug_dump(pprint.pformat(getmembers(packet.cdp)))
            pager.set_line(1, 0, packet.cdp.deviceID)
            line = short_ifname(packet.cdp.PortID)
            if hasattr(packet.cdp, 'native_vlan'):
                line += ', V' + packet.cdp.native_vlan
            pager.set_line(1, 1, line)
            line = ''
            if hasattr(packet.cdp, 'platform'):
                line += packet.cdp.platform
            if hasattr(packet.cdp, 'software_version'):
                line += " (" + packet.cdp.software_version + ")"
                pager.set_line(2, 0, line)
            if ip != '':
                pager.set_line(2, 1, ip)

    if hasattr(packet, 'lldp'):
        logger.debug('New packet is LLDP.')
        capabilities = int(packet.lldp.tlv_system_cap, base=16)
        if capabilities & capability == capability:
            port = ''
            if hasattr(packet.lldp, 'port_id'):
                port = packet.lldp.port_id
            else:
                port = packet.lldp.port_id_mac
            ip = ''
            if hasattr(packet.lldp, 'chassis_id_ip4'):
                ip = packet.lldp.chassis_id_ip4
            elif hasattr(packet.lldp, 'mgn_addr_ip4'):
                ip = packet.lldp.mgn_addr_ip4
            logger.info(
                'Just arrived: LLDP ' + packet.lldp.tlv_system_name + " (" + ip + "), " + port + ", " + packet.lldp.tlv_system_cap)
            if logger.getEffectiveLevel() == logging.DEBUG:
                debug_dump(pprint.pformat(getmembers(packet.lldp)))
            pager.set_line(1, 0, packet.lldp.tlv_system_name)
            line = short_ifname(port)
            if hasattr(packet.lldp, 'media_vlan_id'):
                line += ', V' + packet.lldp.media_vlan_id
            pager.set_line(1, 1, line)
            line = ''
            if hasattr(packet.lldp, 'media_model'):
                line += packet.lldp.media_model
            if hasattr(packet.lldp, 'media_sn'):
                line += " (" + packet.lldp.media_sn + ")"
                pager.set_line(2, 0, line)
            if ip != '':
                pager.set_line(2, 1, ip)


def pager_run():
    global logger, pager, pager_running, has_lcd, has_oled, ip, ip_interface
    ipb = ip
    while pager_running:
        ip_addr = netifaces.ifaddresses(ip_interface)[netifaces.AF_INET][0]
        if 'addr' in ip_addr:
            ipb = ip_addr['addr']
        if ipb != ip:
            logger.info("IP address updated. New IP: " + ipb)
            ip = ipb
            pager.set_line(0, 1, ip)
        page = pager._active_page
        if has_lcd:
            logger.debug("Printing page " + str(page) + " to LCD.")
            lcd.print_buffer(pager.get_active_page())
        if has_oled:
            logger.debug("Printing page " + str(page) + " to OLED.")
            oled.print_buffer(pager.get_active_page())
        pager.next_page()
        time.sleep(3)


def main(argv):
    global has_buzzer, has_fan, has_fan_control, has_oled, has_lcd, lcd, oled, buzzer, fan, fancontrol, pager
    global logger, log_file, cap_interface, capability, config, DIR_PATH, pager_running, ip, ip_interface

    handler = logging.handlers.SysLogHandler(address='/dev/log')
    formatter = logging.Formatter('%(filename)s[%(process)d]:  %(message)s')
    handler.formatter = formatter
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.info('Starting mole app')

    config.read(DIR_PATH + '/mole.ini')
    cap_interface = config.get('GLOBAL', 'cap_interface', fallback='eth0')
    ip_interface = config.get('GLOBAL', 'ip_interface', fallback='br0')
    capability = int(config.get('GLOBAL', 'device_filter', fallback=DEFAULT_FILTER), base=16)
    log_level = config.get('GLOBAL', 'log_level', fallback='INFO')
    if log_level == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    elif log_level == 'INFO':
        logger.setLevel(logging.INFO)
    elif log_level == 'WARNING':
        logger.setLevel(logging.WARNING)
    elif log_level == 'ERROR':
        logger.setLevel(logging.ERROR)
    elif log_level == 'CRITICAL':
        logger.setLevel(logging.CRITICAL)
    log_file = config.get('GLOBAL', 'log_file', fallback='debug.log')

    has_buzzer = config.getboolean('BUZZER', 'enabled', fallback=False)
    has_fan = config.getboolean('FAN', 'enabled', fallback=False)
    has_fan_control = config.getboolean('FAN', 'control', fallback=False)
    has_oled = config.getboolean('OLED', 'enabled', fallback=False)
    has_lcd = config.getboolean('LCD', 'enabled', fallback=False)
    text_width = 0
    text_height = 0

    try:
        opts, args = getopt.getopt(argv, "df:hi:", ["filter=", "iface="])
    except getopt.GetoptError:
        print(HELP)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(HELP)
            sys.exit()
        elif opt == '-d':
            logger.setLevel(logging.DEBUG)
        elif opt in ("-f", "--filter"):
            capability = int(arg, base=16)
        elif opt in ("-i", "--iface"):
            cap_interface = arg

    if has_buzzer:
        buzzer_gpio = config.get('BUZZER', 'BUZZER', fallback=BUZZER.BUZZER.B)
        buzzer = BUZZER.BUZZER(buzzer_gpio)
        buzzer.init()
    if has_fan:
        smbus_addr = config.getint('FAN', 'smbus_addr', fallback=FAN.FAN.SMBUS)
        fan_addr = int(config.get('FAN', 'fan_addr', fallback='0'), base=16)
        if fan_addr == 0:
            fan_addr = FAN.FAN.ADDRESS
        fan = FAN.FAN(smbus_addr, fan_addr)
        if has_fan_control:
            interval = config.getint('FAN', 'interval', fallback=5)
            temp_min = config.getint('FAN', 'temp_min', fallback=FANCONTROL.FANCONTROL.TEMP_MIN)
            temp_max = config.getint('FAN', 'temp_max', fallback=FANCONTROL.FANCONTROL.TEMP_MAX)
            thermal = config.get('FAN', 'thermal', fallback=FANCONTROL.FANCONTROL.THERMAL)
            fancontrol = FANCONTROL.FANCONTROL(fan, interval, temp_min, temp_max, thermal)
            fancontrol.start()
        else:
            fan.on()
    if has_oled:
        width = config.getint('OLED', 'width', fallback=SSD1306.SSD1306.WIDTH)
        height = config.getint('OLED', 'height', fallback=SSD1306.SSD1306.HEIGHT)
        text_width = config.getint('OLED', 'text_width', fallback=SSD1306.SSD1306.TEXT_WIDTH)
        text_height = config.getint('OLED', 'text_height', fallback=SSD1306.SSD1306.TEXT_HEIGHT)
        smbus_addr = config.getint('OLED', 'smbus_addr', fallback=SSD1306.SSD1306.SMBUS_ADDR)
        oled_addr = int(config.get('OLED', 'oled_addr', fallback='0'), base=16)
        if oled_addr == 0:
            oled_addr = SSD1306.SSD1306.ADDRESS
        oled = SSD1306.SSD1306(width, height, smbus_addr, oled_addr, text_width, text_height,
                               DIR_PATH + '/fonts/Courier_New.ttf', 15)
        oled.init()
        oled.clear()
    if has_lcd:
        width = config.getint('LCD', 'width', fallback=LCD1602.LCD1602.WIDTH)
        if text_width < width:
            text_width = width
        height = config.getint('LCD', 'height', fallback=LCD1602.LCD1602.HEIGHT)
        if text_height < height:
            text_height = height
        rs = config.getint('LCD', 'LCD_RS', fallback=LCD1602.LCD1602.RS)
        e = config.getint('LCD', 'LCD_E', fallback=LCD1602.LCD1602.E)
        d4 = config.getint('LCD', 'LCD_D4', fallback=LCD1602.LCD1602.D4)
        d5 = config.getint('LCD', 'LCD_D5', fallback=LCD1602.LCD1602.D5)
        d6 = config.getint('LCD', 'LCD_D6', fallback=LCD1602.LCD1602.D6)
        d7 = config.getint('LCD', 'LCD_D7', fallback=LCD1602.LCD1602.D7)
        addrs = []
        for i in range(height):
            addr = int(config.get('LCD', 'line_' + str(i) + '_addr', fallback='0'), base=16)
            if addr == 0:
                addr = LCD1602.LCD1602.ADDRS[i]
            addrs.insert(i, addr)
        lcd = LCD1602.LCD1602(width, height, rs, e, d4, d5, d6, d7, addrs)
        lcd.init()

    pager = Pager(text_width, text_height, 3)
    pager_running = True
    pager_thread = threading.Thread(target=pager_run, args=())
    pager_thread.daemon = True
    pager_thread.start()

    ip_addr = netifaces.ifaddresses(ip_interface)[netifaces.AF_INET][0]
    if 'addr' in ip_addr:
        ip = ip_addr['addr']

    pager.set_line(0, 0, 'CDP Tester')
    pager.set_line(0, 1, 'Source: ' + cap_interface)

    if has_lcd:
        lcd.print_buffer(pager.get_page(0))
    if has_oled:
        oled.print_buffer(pager.get_page(0))
    time.sleep(1)
    pager.set_line(0, 0, pager.get_line(0, 1))
    pager.set_line(0, 1, ip)
    if has_lcd:
        lcd.print_buffer(pager.get_page(0))
    if has_oled:
        oled.print_buffer(pager.get_page(0))
    if has_buzzer:
        buzzer.background_beep(0.1)

    logger.info('Starting capture on interface ' + cap_interface)
    capture = pyshark.LiveCapture(cap_interface, bpf_filter=CDP_FILTER)
    capture.apply_on_packets(print_packet_info)
    while True:
        capture.sniff_continuously()


def sigterm_handler(_signo, _stack_frame):
    global has_buzzer, has_fan, has_fan_control, has_oled, has_lcd, lcd, fan, buzzer, oled, logger, DIR_PATH
    global pager, pager_running

    pager_running = False
    pager.set_page(0, ["Goodbye!".center(pager.width), " ".ljust(pager.width)])
    if has_lcd:
        lcd.print_buffer(pager.get_page(0))
    if has_oled:
        oled.print_buffer(pager.get_page(0))
    time.sleep(1)
    if has_lcd:
        lcd.finish()
    if has_oled:
        oled.clear()
    if has_fan:
        fan.off()
    logger.info('Mole app ended.')
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, sigterm_handler)
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        sigterm_handler(0, 0)
