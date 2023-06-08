# Pi Mole
This project is intended to use on large networks, where identifying lan endpoint can be painful. The app uses **Cisco CDP** and **LLDP** packets to locate devices and interfaces.

## How it works
The PI after bootup listens on the ethernet interface and catches every CDP and LLDP advertisements. After parsing and filtering these packets if it gets any "interesting" packet, it parses the device info looking for device name, interface name, vlan id, and print those information besides the current IP address of the listening interface.

## Requirements

### Hardware Requirements
To use the device without a power source you will need a **PoE Hat**. To print out details without a screen you'll need an **LCD/OLED** display. 
The following harwares are tested and working properly:
- [Raspberry Pi PoE Hat](https://www.raspberrypi.com/products/poe-hat/)
- [Waveshare PoE hat with OLED Display](https://www.waveshare.com/poe-hat-b.htm)
- [128x32 pixel OLED display](https://www.amazon.com/128x32-SSD1306-Consumption-Display-Arduino/dp/B07PDFCVXL)

### Software Requirements
The system runs on **Raspbian** (or any similar linux distro that can run on a raspberry pi), and uses Python and tshark to acquire network traffic. If you have Python and pip installed you can easily install every package needed.
Required software:
- Raspbian OS or similar
- GPIO driver enabled
- Python
- tshark

Required python packages:
- configparser
- getopt
- pprint
- signal
- threading
- time
- inspect
- netifaces
- pyshark
The following packages are included in the distribution
- LCD1602 driver
- SSD1306 driver

## Configuration
You can use the embedded systemd service to start the app automatically. The included shell cript uses git to pull the latest revision if you checkout the script from a git repo and the system has access to the repository.
To make sure the system never crashes on sudden power loss, you can use read only filesystem or Overlay fs after installation.

To improve usability you can create a bridge interface and use wifi to create an AP to access the wired network on a mobile device.
