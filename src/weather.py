from machine import Pin, I2C, UART
import time
import dht
import machine
from src import util
import bme680


# this class is a controller that coordinates measurements from multiple sensors
# in a specified interval, it checks a number of sensors and sends the measurements to a handler
class Weather:

  # initializes an instance of Weather with the following parameters
  # - an interval which specifies the schedule for measurements
  # - a handler for handling measurements from sensors
  def __init__(self, interval, handler):
    self.last_measurement = None
    self.interval = util.string_to_millis(interval)
    self.handler = handler
    self.sensors = []

  # add a sensor
  def add(self, sensor):
    self.sensors.append(sensor)

  # checks if it's time to measure
  def check(self):
    current_time = time.ticks_ms()
    deadline = time.ticks_add(self.last_measurement, self.interval)
    if self.last_measurement is None or time.ticks_diff(deadline, current_time) <= 0:
      self.measure()
      self.last_measurement = current_time

  # measure everything and send the measurements to the handler
  def measure(self):
    data = {}
    for sensor in self.sensors:
      measurement = sensor.measure()
      print(measurement)
      data = data | measurement

    if self.handler is not None:
      self.handler.handle(data)


# the class measures temperature and humidity with DHT22 sensor
class DHT22Sensor:

  # initializes a new instance
  def __init__(self, pin):
    self.dht22 = dht.DHT22(machine.Pin(pin))

  # measure temperature and humidity
  def measure(self):
    self.dht22.measure()
    c = self.dht22.temperature()
    h = self.dht22.humidity()
    f = int((c * 1.8) + 32)
    print('centigrade  = %.2f' % c)
    print('farenheit   = %.2f' % f)
    print('humidity    = %.2f' % h)
    return [c, h, f]
    
# the class measures temperature, pressure, gas and humidity with BME680 sensor
class BME680Sensor:

  # initializes a new instance
  def __init__(self, sda_pin, scl_pin):
    self.dht22 = dht.DHT22(machine.Pin(sda_pin), )
    i2c = I2C(0,sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)    #initializing the I2C method 
    self.bme = bme680.BME680_I2C(i2c, address=0x76)

  # measure temperature, pressure, gas and humidity
  def measure(self):
    temperature = str(round(self.bme.temperature, 2))
    humidity = str(round(self.bme.humidity, 2))
    pressure = str(round(self.bme.pressure, 2))
    gas = str(round(self.bme.gas/1000, 2))
    print('Temperature:', temperature)
    print('Humidity:', humidity)
    print('Pressure:', pressure)
    print('Gas:', gas)
    # self.dht22.measure()
    # c = self.dht22.temperature()
    # h = self.dht22.humidity()
    # f = int((c * 1.8) + 32)
    # print('centigrade  = %.2f' % c)
    # print('farenheit   = %.2f' % f)
    # print('humidity    = %.2f' % h)
    return {'temperature': temperature, 'humidity': humidity, 'pressure': pressure, 'gas': gas}


# this class measures CO2 with MH-Z19B sensor
class MHZ19BSensor:

    # initializes a new instance
    def __init__(self, tx_pin, rx_pin, lights, co2_threshold):
        print(tx_pin, rx_pin)
        self.uart = UART(0, baudrate=9600, bits=8, parity=None, stop=1, tx=int(tx_pin), rx=int(rx_pin))
        self.lights = lights
        self.co2_threshold = int(co2_threshold)

    # measure CO2
    def measure(self):
        while True:
            # noise = self.uart.read()
            # print('noise', noise)
            # send a read command to the sensor
            self.uart.write(b'\xff\x01\x86\x00\x00\x00\x00\x00\x79')
            # self.uart.write(b'\xff\x01\x79\x00\x00\x00\x00\x00\xe6')

            # a little delay to let the sensor measure CO2 and send the data back
            time.sleep(1)  # in seconds

            # read and validate the data
            buf = self.uart.read(9)
            print(buf)
            if self.is_valid(buf):
                break
            
            # retry if the data is wrong
            self.lights.error_on()
            print('error while reading MH-Z19B sensor: invalid data')
            print('retry ...')

        self.lights.error_off()

        co2 = buf[2] * 256 + buf[3]
        print('co2         = %.2f' % co2)

        # turn on the LED if the CO2 level is higher than the threshold
        if co2 > self.co2_threshold:
            self.lights.high_co2_on()
        else:
            self.lights.high_co2_off()

        return [co2]

    # check data returned by the sensor
    def is_valid(self, buf):
        if buf is None or buf[0] != 0xFF or buf[1] != 0x86:
            return False
        i = 1
        checksum = 0x00
        while i < 8:
            checksum += buf[i] % 256
            i += 1
        checksum = ~checksum & 0xFF
        checksum += 1
        return checksum == buf[8]