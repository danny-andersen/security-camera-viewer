#!/usr/bin/env python3

from time import sleep
from gpiozero import Button
from signal import pause
import os

GPIO_PIN=17

#Wait for system to stabilize and allow GPIO to be ready
#Also allows time for user to stop this service if GPIO not connected
print("GPIO shutdown service - waiting 120 seconds for system to stabilize...")
sleep(120)

# Use BCM pin 17 (physical pin 11)
shutdown_pin = Button(17, pull_up=True)

# Track how long the pin has been LOW
low_duration = 0
check_interval = 1  # seconds
threshold = 15      # seconds

print("GPIO shutdown service started. Monitoring pin state...")
while True:
    if shutdown_pin.is_pressed:  # LOW state
        low_duration += check_interval
        print(f"GPIO shutdown service: Pin LOW for {low_duration} seconds")
        if low_duration >= threshold:
            print(f"Pin LOW for {low_duration} seconds. Shutting down in 60 seconds...")
            os.system('shutdown +1 "System is shutting down due to GPIO $GPIO_PIN signal."')
            break
    else:
        if low_duration > 0:
            print("Pin returned HIGH. Resetting timer.")
        low_duration = 0
    sleep(check_interval)

pause()
