#!/bin/bash

#
# GPIO Shutdown Script
# This script monitors a specified GPIO pin and initiates a system shutdown
# when the pin reads LOW (0V).
#
# Configuration
# - GPIO_PIN: The GPIO pin number to monitor.
GPIO_PIN=17

# Sleep duration between checks (in seconds)
SLEEP_DURATION=1

#Wait for system to stabilize and allow GPIO to be ready
#Also allows time for user to stop this service if GPIO not connected
sleep 120

# Export and configure the pin
if [ ! -d /sys/class/gpio/gpio$GPIO_PIN ]; then
    echo "$GPIO_PIN" > /sys/class/gpio/export
    sleep 0.1
fi

echo "in" > /sys/class/gpio/gpio$GPIO_PIN/direction

# Loop to check every second
while true; do
    PIN_VALUE=$(cat /sys/class/gpio/gpio$GPIO_PIN/value)
    if [ "$PIN_VALUE" -eq 0 ]; then
        echo "GPIO $GPIO_PIN is LOW. Shutting down..."
        #Initiate a shutdown in 60 seconds to notify users
        shutdown +1 "System is shutting down due to GPIO $GPIO_PIN signal."
        break
    fi
    sleep $SLEEP_DURATION
done
# Unexport the pin (optional, won't be reached due to shutdown)
echo "$GPIO_PIN" > /sys/class/gpio/unexport 2>/dev/null
