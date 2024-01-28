import uos
import machine
import utime
from machine import Pin, I2C
import bme680
import urequests
from src.wifi import connect
from ds3231 import DS3231
import time

# rtc_i2c = I2C(1, sda=Pin(2), scl=Pin(3))
# rtc = DS3231(rtc_i2c)
recv_buf="" # receive buffer global variable

print()
print("Machine: \t" + uos.uname()[4])
print("MicroPython: \t" + uos.uname()[3])

ip = connect()
i2c=I2C(0,sda=Pin(0), scl=Pin(1), freq=400000)    #initializing the I2C method 
#utime.sleep_ms(100)

print(i2c.scan())
bme = bme680.BME680_I2C(i2c, address=0x76)
print(bme)
while True:
  utime.sleep(2.0)
#   timeNow = rtc.datetime()
  # temperature = str(round(bme.temperature, 2)) + ' C'
  # humidity = str(round(bme.humidity, 2)) + ' %'
  # pressure = str(round(bme.pressure, 2)) + ' hPa'
  # gas = str(round(bme.gas/1000, 2)) + ' KOhms'
  temperature = str(round(bme.temperature, 2))
  humidity = str(round(bme.humidity, 2))
  pressure = str(round(bme.pressure, 2))
  gas = str(round(bme.gas/1000, 2))
  print('Temperature:', temperature)
  print('Humidity:', humidity)
  print('Pressure:', pressure)
  print('Gas:', gas)
#   print('Time:', timeNow)
#   epoch_time = utime.mktime(timeNow) * 1000000000
#   print("Unix Epoch Time:", epoch_time)
  print('-------')
  url = "http://192.168.0.236:8086/api/v2/write?org=env_org&bucket=picow_sensors&precision=ns"
  headers = {
      "Authorization": "Token 2XlhYIByAVr5IOgB0ST12F7FDFVdtx3wm9SEMjivLb4lVhg1ww334VeT12Ydl9dkuonKkVGHY3NGv5fXHKp5yg==",
      "Content-Type": "text/plain; charset=utf-8",
      "Accept": "application/json"
  }
  # data = '''
  #     airSensors,sensor_id=TLM0201 temperature=73.97038159354763,humidity=35.23103248356096,co=0.48445310567793615 1706276176000000000
  #     airSensors,sensor_id=TLM0202 temperature=75.30007505999716,humidity=35.651929918691714,co=0.5141876544505826 1706276179900000000
  # '''
  data = f'''
      airSensors,sensor_id=TLM0201 temperature={temperature},humidity={humidity},pressure={pressure},gas={gas}
  '''

  response = urequests.post(url, headers=headers, data=data)
  print(response.text)
  response.close()