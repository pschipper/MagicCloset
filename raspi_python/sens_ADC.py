#!/usr/bin/python
 
import spidev
import time
import os

class ADC:
 
 	def __init__(self, debug=False):
		self.debug = debug
		self.spi = spidev.SpiDev()
		self.spi.open(0,0)
		self.spi.max_speed_hz=1000000

	# Function to read SPI data from MCP3008 chip
	# Channel must be an integer 0-7
	def readChannel(self, channel):
		adc = self.spi.xfer2([1,(8+channel)<<4,0])
		data = ((adc[1]&3) << 8) + adc[2]

		# Convert bits to volts
		volts = (data * 3.3) / float(1023)
		return volts

	# Reads channel and converts to percent light
	def readLight(self):
		volts = self.readChannel(1)
		light = volts / 3.3 * 100
		return light

	# Reads channel and converts to percent moisture
	def readMoisture(self,):
		volts = self.readChannel(0)
		moisture = volts / 3.3 * 100
		return moisture

	def close(self):
		self.spi.close()