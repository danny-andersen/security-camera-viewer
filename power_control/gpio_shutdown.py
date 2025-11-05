#!/usr/bin/env python3

from time import sleep
from gpiozero import Button
from signal import pause
import os

#Wait for system to stabilize and allow GPIO to be ready
#Also allows time for user to stop this service if GPIO not connected
sleep(120)

# Use BCM pin 17 (physical pin 11)
shutdown_pin = Button(17, pull_up=False)

def shutdown():
    print("GPIO 17 is LOW. Shutting down...")
    os.system("sudo shutdown -h now")

# Trigger shutdown when pin goes LOW
shutdown_pin.when_released = shutdown

# Keep the script running
pause()
