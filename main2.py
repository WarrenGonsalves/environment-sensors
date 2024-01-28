from src.weather import Weather
from src.weather import BME680Sensor, MHZ19BSensor
from src.config import Config
from src.lights import Lights
from machine import Pin
import urequests
# from wifi import AccessPoint
from src.wifi import Connection
import gc
import time
from src import util
import sys
import uerrno


# the handle() method below takes temperature and humidity
# and writes them to a spreadsheet
#
# the following function, when added to the google sheet (Tools > Script editor) allows the
# formula uploaded in the "now" variable (see "measure(self)") to calculate a local timestamp
# from the epoch value loaded in column A of the inserted row
#
# function TIMESTAMP_TO_DATE(value) {
#   return new Date(value * 1000);
# }
# see the sheets.py file to set the ValueInputOption to USER_INPUT to avoid now string value being prefixed with a '
class WeatherHandler:

    # initializes a new handler
    def __init__(self, url, org, bucket, token):
        self.url = url
        self.org = org
        self.bucket = bucket
        self.token = token

    # send data to the sheet
    def handle(self, data):
      url = f"http://{self.url}/api/v2/write?org={self.org}&bucket={self.bucket}&precision=ns"
      headers = {
        "Authorization": f"Token {self.token}",
        "Content-Type": "text/plain; charset=utf-8",
        "Accept": "application/json"
      }
      print(f"data in weatherhandler {data['temperature']}")
      data = f'''
        airSensors,sensor_id=TLM0201 temperature={data['temperature']},humidity={data['humidity']},pressure={data['pressure']},gas={data['gas']}
      '''

      response = urequests.post(url, headers=headers, data=data)
      print(response.text)
      response.close()


# enable garbage collection
gc.enable()
print('garbage collection threshold: ' + str(gc.threshold()))

# load configuration for a file
config = Config('main.conf')
# initialize an interface to LEDs
lights = Lights(config.get('wifi_led_pid'),
                config.get('error_led_pid'),
                config.get('high_co2_led_pin'))
lights.off()

# create a handler which takes temperature and humidity and write them to a sheet
weather_handler = WeatherHandler(
                config.get('influxdb_url'),
                config.get('influxdb_org'),
                config.get('influxdb_bucket'),
                config.get('influxdb_token'))

# initialize available sensors and add them to a controller
weather = Weather(config.get('measurement_interval'),
                  weather_handler)
# if config.get('bme680_sda_pin') and config.get('bme680_scl_pin'):
weather.add(BME680Sensor(config.get('bme680_sda_pin'), config.get('bme680_scl_pin')))
print('registered a BME680 sensor')

# if config.get('mhz19b_tx_pin') and config.get('mhz19b_rx_pin'):
#     weather.add(MHZ19BSensor(config.get('mhz19b_tx_pin'),
#                              config.get('mhz19b_rx_pin'),
#                              lights,
#                              config.get('co2_threshold')))
#     print('registered a MH-Z19B sensor')

# initialize a switch which turns on the configuration mode
# if the switch changes its state, then the board is going to reboot immediately
# config_mode_switch = Pin(config.get('config_mode_switch_pin'), Pin.IN)
# config_mode_switch.irq(lambda pin: util.reboot())

# first, check if the configuration mode is enabled
# if so, set up an access point, and then start an HTTP server
# the server provides a web form which updates the configuration of the device
# the server runs on http://192.168.4.1:80
# if config_mode_switch.value() == 1:
#     from http.server import HttpServer
#     from settings import ConnectionHandler
#     print('enabled configuration mode')

#     access_point = AccessPoint(config.get('access_point_ssid'),
#                                config.get('access_point_password'))
#     access_point.start()
#     lights.wifi_on()
#     handler = ConnectionHandler(config, lights)
#     HttpServer(access_point.ip(), 80, handler).start()
#     lights.wifi_off()
#     util.reboot()


# try to connect to WiFi if the configuration mode is disabled
wifi = Connection(config.get('ssid'), config.get('password'), lights)
wifi.connect()

# finally, start the main loop
# in the loop, the board is going to check temperature and humidity
error = False
while True:
    try:
        # reconnect if a error occurred or the connection is lost
        if error or not wifi.is_connected():
            wifi.reconnect()

        error = False
        lights.error_off()
        weather.check()
    except Exception as e:
        error = True
        lights.error_on()
        print('achtung! something wrong happened! ...')
        sys.print_exception(e)
        if isinstance(e, OSError) and e.args[0] in uerrno.errorcode:
            print('error code: %s' % uerrno.errorcode[e.args[0]])
        if config.get('error_handling') == 'reboot':
            print('rebooting ...')
            util.reboot()
        elif config.get('error_handling') == 'stop':
            print('stop ...')
            raise
        else:
            print('continue ...')

        # a little delay
        time.sleep(3)