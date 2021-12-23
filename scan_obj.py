#!/usr/bin/env python
"""
Description: This program works as a driver software for a simple 3d scanner based off of the SuperMakeSomething build found at: 
			https://github.com/SuperMakeSomething/diy-3d-scanner/blob/master/scannerCode.ino
			It has been designed to function on a Raspberry Pi rather than arduino, and writes the scan data to a local file rather than SD card.
			The build this code was designed around uses two 28BYJ-48 motors and ULN2003APG driver boards. The scanner is a Sharp GP2Y0A51SK0F.
			It is necessary to use an ADC with the scanner to convert analog return to a digital voltage measurement.
			The rotate function here is a derivative of https://github.com/Basch3000/raspberry-pi-projects/blob/master/motordeg.py
Author: Daniel Schenk
Date: 7 December 2021
"""
from time import sleep
import RPi.GPIO as GPIO
import smbus2 as smbus
from math import pow
import os
 
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

motor1 = [4, 17, 27, 22]			# GPIO pins of Z axis motor
motor2 = [5, 6, 13, 19]				# GPIO pins of object platform motor
motorpins = [4, 17, 27, 22, 5, 6, 13, 19]	# This extra list of all motor pins lets me remove 2 for loops and 6 lines of code initializing/closing pins
filename = 'scanfile.txt'			# Name of file to write scan data to
ZMAX = 105 					# Maximum verical increments for scanning, each approx 1mm vert height 

for pin in motorpins:				# Set all necessary GPIO pins to output mode
	GPIO.setup(pin,GPIO.OUT)
	GPIO.output(pin, False)

aSequence = [[1,0,0,1],	[1,0,0,0],	[1,1,0,0],	[0,1,0,0],	[0,1,1,0],	[0,0,1,0],	[0,0,1,1],	[0,0,0,1]]     
iNumSteps = len(aSequence)

"""motor is a list of pins, speed 1 is full speed (higher num is slower), iDeg is number of steps to turn motor - 4096 steps=360 degrees, 
iDirection 1 is cw (up on Z), -1 is ccw (down on Z), 600 steps is approx 1mm vertical travel on z axis
pos is not needed for this build but left here for future options"""
def rotate(motor, speed, iDeg, iDirection, pos = None):
	fWaitTime = int(speed) / float(1000)

	iSeqPos = 0
	if pos is not None:			# The iSeqPos argument is used for granular control of where a motor begins at each operation
		iSeqPos = int(pos)		# It is left here for potential use in future builds

	for step in range(0,iDeg):		# Activates motor coils according to bitmapping in aSequence and required number of steps
		for iPin in range(0, 4):
			iRealPin = motor[iPin]
			if aSequence[iSeqPos][iPin] != 0:
				GPIO.output(iRealPin, True)
			else:
				GPIO.output(iRealPin, False)
		
		iSeqPos += iDirection		# Again iSeqPos not really needed here but could be useful to import this fun to other projects
		if (iSeqPos >= iNumSteps):
			iSeqPos = 0
		if (iSeqPos < 0):
			iSeqPos = iNumSteps + iDirection

		sleep(fWaitTime)		# Micro-sleeps to control motor rotation speed


"""Scans the object 50 times, uses ADC to convert analog value to digital voltage, quadrature equation to convert voltage to distance, and returns the average of the scans"""
def scan():
	data = 0
	temp = 0
	try:
		with smbus.SMBus(1) as bus:
			for dist in range(50):				# Take 50 scans, scanner is finnicky, averaging the 50 scans gives more consistent results
				sleep(0.01)  				# Sleep here helps prevent errors
				bus.write_byte(0x4b, 0x8f)  		# send command byte to ADC for correct address and channel per documentation
				temp = float(bus.read_byte(0x4b)/100)	# read the converted value back, cast to float and convert to represent voltage
				temp = -5.40274*pow(temp, 3)+28.4823 * pow(temp, 2)-49.7115*temp+31.3444   # Quadrature equation to convert voltage to distance
				data += temp				# Add each scan to data to be averaged before return
			return(round((data/50), 2))
	except OSError:
		return(0)


def main():
	z_current = 0
	last_valid = 0
	dist = 0
	with open(filename, 'w') as scanfile: 				# Open file to write scan data to
		while z_current < ZMAX:					# Loop until scanner reaches desired vertical maximum
			for step in range(256):				# 256 * 16 steps is a full rotation
				dist = scan()				# Scan current point of object
				if dist is not 0:			# Make sure scan returned valid data
					last_valid = dist		# If newest data is valid, assign it to last_valid
				scanfile.write(str(last_valid)+"\n")	# Write most recent valid data to scanfile
				print(step, last_valid)			# Debugging
				rotate(motor2, 1, 16, 1)		# Turn object platform by 16 steps (~1.41 degrees) clockwise, full speed

				if step == 255:				# If one full rotation of platform has occured
					scanfile.write("9999.00\n")	# Write layer delimiter to file
					z_current+= 1			# Increment vertical position counter
					step = 0			# Reset rotational counter
					rotate(motor1, 1, 600, 1)	# Increase z-axis, 600 steps = approx 1 mm
					sleep(1)			# Give everything a second to finish moving

	for pin in motorpins:
		GPIO.output(pin, False)


if __name__ == '__main__':
	main()
