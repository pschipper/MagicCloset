#!/usr/bin/env python3 
#coding=utf-8

import time
import pigpio 

#python class for Si7021 Temp-Humidity Sensor

class SI7021:
	
	#sensor has fixed address
	address = 0x40
	maxHeatLevel = 2 #this is 16mA, enough for me.. 15 would be 95 (!!) mA

	#RH Conversion Times
	#max conversion time for RH reading. In ms. 12,11,10 and 8 bit
	HtConvRh = 100 # 12
	MHtConvRh = 100 # 7
	MLtConvRh = 100 # 4.5
	LtConvRh = 100 # 3.1

	#Temp Conversion Times
	#max conversion time for TEMP reading. In ms. 14,13,12 and 11 bit
	HtConvTemp = 100 # 10.8
	MHtConvTemp = 100 # 6.2
	MLtConvTemp = 100 # 3.8
	LtConvTemp = 100 # 2.4

	HtConvFull = HtConvRh + HtConvTemp
	MHtConvFull = MHtConvRh + MHtConvTemp
	MLtConvFull = MLtConvRh + MLtConvTemp
	LtConvFull = LtConvRh + LtConvTemp
	
	#time of powerup after reset. In ms.
	resetTime = 15
	
	#commands
	HumHoldCmd = 0xE5 #Measure Relative Humidity, Hold Master Mode
	HumNoHoldCmd = 0xF5 #Measure Relative Humidity, No Hold Master Mode 
	TempHoldCmd = 0xE3 #Measure Temperature, Hold Master Mode 
	TempNoHoldCmd = 0xF3 #Measure Temperature, No Hold Master Mode 
	TempLastRhCmd = 0xE0 #Read Temperature Value from Previous RH Measurement 
	SensorResetCmd = 0xFE
	'''
	D7-D0 Measurement Resolution:
		RH 		Temp
	00	12 bit	14 bit
	01	 8 bit 	12 bit
	10	10 bit 	13 bit
	11	11 bit 	11 bit

	D2 HTRE 
	1 = On-chip Heater Enable
	0 = On-chip Heater Disable
	'''
	WriteUserRegCmd = 0xE6 #Write User Register
	ReadUserRegCmd = 0xE7 #Read User Register
	'''
	For heater, write 4 LSB of register. From 0000 to 1111, from 3mA to 95mA power consumption
	'''
	WriteHeatRegCmd = 0x51 #Write Heater Control Register
	ReadHeatRegCmd = 0x11 #Read Heater Control Register 
	FirmwareRevCmd = [0x84,0xB8] #Read Firmware Revision  
	'''
	checksum byte is calculated using a CRC generator polynomial of x8 + x5 + x4 + 1, with an initialization of 0x00
	'''
	ReadIDlowCmd = [0xFA,0x0F] #Read Electronic ID 1st Byte  
	ReadIDhighCmd = [0xFC,0xC9] #Read Electronic ID 2nd Byte  

	def __init__(self, bus=1, debug=False):
		self.debug = debug
		self.pi = pigpio.pi()
		self.i2c = self.pi.i2c_open(bus, self.address, 0)

	def resetSensor(self):
		self.pi.i2c_write_device(self.i2c, [self.SensorResetCmd])
		time.sleep(self.resetTime/1000.0)

	def readRH(self,hold=False):
		#check what resolution is set up
		resolution = self.getRes()
		if resolution == 0b00: sleepTime = self.HtConvFull/1000.0
		elif resolution == 0b01: sleepTime = self.MHtConvFull/1000.0
		elif resolution == 0b10: sleepTime = self.MLtConvFull/1000.0
		else: sleepTime = self.LtConvFull/1000.0
		#now start a new conversion
		if hold: command = self.HumHoldCmd
		else: command = self.HumNoHoldCmd
		self.pi.i2c_write_device(self.i2c, [command])
		#wait for the reading to end
		time.sleep(sleepTime)
		c, rh = self.pi.i2c_read_device(self.i2c, 3) # msb, lsb, checksum		
		#check the checksum.. to be implemented		
		if self.checkChecksum(rh) > 0:
			raise Exception("Wrong Checksum in RH reading")
		value = (rh[0]<<8) + rh[1]
		return min(max(0.0,((125.0*value)/65536.0)-6.0),100.0)
		
	def readTemp(self,hold=False,last=False,checksum=False):
		#i'f i'm requesting the last converted temp (in a RH read) i can skip half function
		if last: 
			command = self.TempLastRhCmd
			sleepTime = 0
		else:
			#check what resolution is set up
			resolution = self.getRes()
			if resolution == 0b00: sleepTime = self.HtConvTemp/1000.0
			elif resolution == 0b01: sleepTime = self.MHtConvTemp/1000.0
			elif resolution == 0b10: sleepTime = self.MLtConvTemp/1000.0
			else: sleepTime = self.LtConvTemp/1000.0
			#now start a new conversion
			if hold: command = self.TempHoldCmd
			else: command = self.TempNoHoldCmd
		self.pi.i2c_write_device(self.i2c, [command])
		#wait for the reading to end
		time.sleep(sleepTime)
		c, t = self.pi.i2c_read_device(self.i2c, 3) # msb, lsb, checksum		
		#check the checksum.. to be implemented reading IDs
		if self.checkChecksum(t) > 0:
			raise Exception("Wrong Checksum in Temp reading")
		value = (t[0]<<8) + t[1]
		return ((175.72*value)/65536.0)-46.85
	
	def readUserReg(self):
		self.pi.i2c_write_device(self.i2c, [self.ReadUserRegCmd])
		regValue = self.pi.i2c_read_byte(self.i2c) # reg value
		return regValue

	def readHeatReg(self):
		self.pi.i2c_write_device(self.i2c, [self.ReadHeatRegCmd])
		regValue = self.pi.i2c_read_byte(self.i2c) # reg value
		return regValue

	def writeUserReg(self,data):
		self.pi.i2c_write_device(self.i2c, [self.WriteUserRegCmd, data])

	def writeHeatReg(self,data):
		if data > maxHeatLevel: raise ValueError("Heat Level too high")
		self.pi.i2c_write_device(self.i2c, [self.writeHeatRegCmd, data])
		
	def setRes(self,resolution):
		#we have 4 levels. 0-3? but inverted (in the reg 00 is the highest)
		if resolution not in range(0,4): raise ValueError("Resolution must be in range 0-3")
		#inverting the range
		resolution = 3-resolution
		#exploding bits
		resMSB = resolution>>1&1
		resLSB = resolution&1
		#getting actual register
		reg = self.readUserReg()
		#bitwising it
		reg = self.setBit(reg,resMSB,7)
		reg = self.setBit(reg,resLSB,0)
		#writing it back to the device
		self.writeUserReg(reg)
		
	def getRes(self):
		userReg = self.readUserReg()
		return((userReg>>0&1) | (userReg>>7&1)<<1)
		
	def heaterControl(self,power=0,level=0):
		#power control!
		#getting actual register
		reg = self.readUserReg()
		#bitwising it
		reg = self.setBit(reg,power,2)
		#writing it back to the device
		self.writeUserReg(reg)		
		#level control
		self.writeHeatReg(level)
		
	def checkChecksum(self,data):
		rem = 0
		for b in data:
			rem ^= b
			for bit in range(8):
				if rem & 128:
					rem = (rem << 1) ^ 0x131
				else:
					rem = (rem << 1)
		return rem & 0xFF	
		
	def getFirmwareRev(self):
		self.pi.i2c_write_device(self.i2c, self.FirmwareRevCmd)
		regValue = self.pi.i2c_read_byte(self.i2c) # reg value
		return regValue
		
	def getSerial(self):
		self.pi.i2c_write_device(self.i2c, self.ReadIDlowCmd)
		c, resultLow = self.pi.i2c_read_device(self.i2c, 8)
		self.pi.i2c_write_device(self.i2c, self.ReadIDhighCmd)
		c, resultHigh = self.pi.i2c_read_device(self.i2c, 6)

		crc = (resultLow[1],resultLow[3],resultLow[5],resultLow[7],resultHigh[2],resultHigh[5])
		serial = (resultLow[0],resultLow[2],resultLow[4],resultLow[6],resultHigh[0],resultHigh[1],resultHigh[3],resultHigh[4])
		if 	self.checkChecksum((resultLow[0],resultLow[1])) or \
			self.checkChecksum((resultLow[0],resultLow[2],resultLow[3])) or \
			self.checkChecksum((resultLow[0],resultLow[2],resultLow[4],resultLow[5])) or \
			self.checkChecksum((resultLow[0],resultLow[2],resultLow[4],resultLow[6],resultLow[7])) or \
			self.checkChecksum((resultHigh[0],resultHigh[1],resultHigh[2])) or \
			self.checkChecksum((resultHigh[0],resultHigh[1],resultHigh[3],resultHigh[4],resultHigh[5])): 
			raise Exception("Checksum error in Serial")
		return (resultLow[0]<<56)|(resultLow[2]<<48)|(resultLow[4]<<40)|(resultLow[6]<<32)|(resultHigh[0]<<24)|(resultHigh[1]<<16)|(resultHigh[3]<<8)|resultHigh[4]
		
	def setBit(self,byte,bit,index):
		#Set the index:th bit of byte to bit, and return the new value.
		mask = 1 << index
		byte &= ~mask
		if bit:
			byte |= mask
		return byte

	def close(self):
		self.pi.i2c_close(self.i2c)
		self.pi.stop()

if __name__ == "__main__":
	sensor = SI7021()
	print("Temp {}".format(sensor.readTemp()))
	print("RH: {}".format(sensor.readRH()))
	sensor.close()