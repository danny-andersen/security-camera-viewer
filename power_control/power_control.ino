#include <Arduino.h>
#define DEBUG false
#include "comms.h"

#define VSENSE_IN 3     // Connected to TV USB output - high when TV is on, low when off
#define PICONTROL_OUT 4 // Tells the raspberry pi whether to shutdown or not. Must be high when the PI boots. Driving it low tells the PI to shutdown immediately
#define RELAY_OUT 5     // Controls the power to the PI
#define RED_LED 6
#define GREEN_LED 7
#define BLUE_LED 8

#define RELAY_ON HIGH // Relay is low level triggered but is controlled via a transistor that needs to be driven high
#define RELAY_OFF LOW
#define TV_IS_ON LOW   // When TV is on, this line is driven low
#define TV_IS_OFF HIGH // When TV is off, this line is pulled high

const unsigned long LOOP_DELAY = 1000;                  // 1 sec loop time
const unsigned long BOOT_DELAY = 300000;                // 5 mins boot up and settle time - minimum on period - will not enter a power off cycle until this has elapsed
const unsigned long SHUTDOWN_DELAY = 120000;            // 2 mins shutdown time - will hold the power on for this period whilst the PI shutsdown and will not enter a new power on cycle
const unsigned long TV_AND_CAMERA_OFF_DEADBAND = 30000; // 30 seconds wait time after TV goes off before telling PI to power down
unsigned long waitTime = 0;

enum Colours
{
  OFF,
  RED,
  YELLOW,
  GREEN,
  BLUE,
};

enum State
{
  INIT,
  TV_AND_CAMERA_OFF,
  TV_OR_CAMERA_ON,
  POWER_ON_PI,
  POWER_ON_PI_WAIT,
  POWER_OFF_PI,
  POWER_OFF_PI_WAIT,
};

#define IDNAME(name) #name
const char *stateNames[] = {IDNAME(INIT), IDNAME(TV_AND_CAMERA_OFF), IDNAME(TV_OR_CAMERA_ON), IDNAME(POWER_ON_PI), IDNAME(POWER_ON_PI_WAIT), IDNAME(POWER_OFF_PI), IDNAME(POWER_OFF_PI_WAIT)};

int state = INIT;
int newState = state;
uint8_t relayState = 0;  // Current state of the relay controlling power to the PI
uint8_t cameraState = 0; // Whether a remote command has been received to power on the PI (so that the camera comes on)
uint8_t tvState = 0;     // Whether the TV is on or off (and so whether to power on the PI to start up the camera viewer display)

void setup()
{
  if (DEBUG)
    Serial.begin(115200);
  pinMode(VSENSE_IN, INPUT_PULLUP);
  pinMode(PICONTROL_OUT, OUTPUT);
  pinMode(RED_LED, OUTPUT);   // Initialize the LED pin as an output
  pinMode(GREEN_LED, OUTPUT); // Initialize the LED pin as an output
  pinMode(BLUE_LED, OUTPUT);  // Initialize the LED pin as an output
  pinMode(RELAY_OUT, OUTPUT); // Initialize the RELAY pin as an output

  digitalWrite(PICONTROL_OUT, LOW);
  digitalWrite(RELAY_OUT, RELAY_OFF);
  setLED(RED);

  comms_init();
  state = INIT;
  newState = INIT;
}

void loop()
{
  tvState = digitalRead(VSENSE_IN);
  if (DEBUG)
  {
    Serial.print("State: ");
    Serial.print(stateNames[state]);
    Serial.print(" , TV is ");
    Serial.print(tvState ? "OFF" : "ON");
    Serial.print(" , Camera is ");
    Serial.println(cameraState ? "ON" : "OFF");
  }
  unsigned long delayTime = LOOP_DELAY;
  switch (state)
  {
  case (INIT):
    if (tvState == TV_IS_ON || cameraState == 1)
    {
      newState = POWER_ON_PI;
    }
    else
    {
      newState = TV_AND_CAMERA_OFF;
    }
    break;
  case (POWER_ON_PI):
    // TV has been switched on, power on the PI
    digitalWrite(PICONTROL_OUT, LOW);
    digitalWrite(RELAY_OUT, RELAY_ON);
    relayState = 1;
    setLED(BLUE);
    newState = POWER_ON_PI_WAIT;
    waitTime = BOOT_DELAY;
    break;
  case (POWER_ON_PI_WAIT):
    // Time deadband to allow PI time to boot up and load any security patches etc
    waitTime -= LOOP_DELAY;
    if (waitTime <= 0 && (tvState == TV_IS_ON || cameraState == 1))
    {
      newState = TV_OR_CAMERA_ON;
      delayTime = 10;
    }
    if (waitTime <= 0 && tvState == TV_IS_OFF && cameraState == 0)
    {
      newState = POWER_OFF_PI;
      delayTime = 10;
    }
    break;
  case (TV_OR_CAMERA_ON):
    if (tvState == TV_IS_OFF && cameraState == 0)
    {
      // Turn the PI off after a small time deadband
      waitTime = TV_AND_CAMERA_OFF_DEADBAND;
      do
      {
        delay(LOOP_DELAY);
        waitTime -= LOOP_DELAY;
        tvState = digitalRead(VSENSE_IN);
        checkCameraState(LOOP_DELAY);
        if (DEBUG)
        {
          Serial.print("State is TV_OR_CAMERA_ON and waiting to see if TV or Camera comes back on: TV is ");
          Serial.print(tvState ? "OFF" : "ON");
          Serial.print(" , Camera is ");
          Serial.println(cameraState ? "ON" : "OFF");
        }
      } while (waitTime > 0 && tvState == TV_IS_OFF && cameraState == 0);
      waitTime = 0;
      // Re-read the sense input. If TV is still off then signal PI to shutdown
      // This provides a time deadband on the sense input to allow the USB cable to unplugged and replugged in
      if (tvState == TV_IS_OFF && cameraState == 0)
      {
        newState = POWER_OFF_PI;
      }
    }
    break;
  case (POWER_OFF_PI):
    digitalWrite(PICONTROL_OUT, HIGH);
    setLED(YELLOW);
    waitTime = SHUTDOWN_DELAY;
    newState = POWER_OFF_PI_WAIT;
    break;
  case (POWER_OFF_PI_WAIT):
    // Time deadband to wait for PI to recognise shutdown has been signalled and to perform a controlled shutdown
    waitTime -= LOOP_DELAY;
    if (waitTime <= 0)
    {
      newState = TV_AND_CAMERA_OFF; // Regardless of whether TV has come on or not, power off the PI as the PI will have shutdown
      delayTime = 10;
    }
    break;
  case (TV_AND_CAMERA_OFF):
    if (tvState == TV_IS_ON || cameraState == 1)
    {
      newState = POWER_ON_PI;
    }
    break;
  }
  // Serial.print("New State: ");
  // Serial.print(stateNames[newState]);
  // Serial.println(" Sleeping..");

  delay(delayTime);

  if (state == POWER_ON_PI_WAIT && newState == TV_OR_CAMERA_ON)
  {
    setLED(GREEN);
  }
  if (state == POWER_OFF_PI_WAIT && newState == TV_AND_CAMERA_OFF)
  {
    digitalWrite(RELAY_OUT, RELAY_OFF);
    relayState = 0;
    setLED(RED);
    delay(5000); // Ensure PI is powercycled
    delayTime += 5000;
  }
  checkCameraState(delayTime);
  state = newState;
}

void checkCameraState(unsigned long delayTime)
{
  uint8_t newPowerState = comms_loop(delayTime, relayState, cameraState);
  if (newPowerState != cameraState)
  {
    if (DEBUG)
    {
      Serial.print("Received new camera state: ");
      Serial.println(newPowerState);
    }
    cameraState = newPowerState;
  }
}

void setLED(Colours colour)
{
  if (DEBUG) {
    Serial.print("Setting colour to ");
    Serial.println(colour);
  }
  switch (colour)
  {
  case (OFF):
    digitalWrite(RED_LED, LOW);
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(BLUE_LED, LOW);
    break;
  case (RED):
    digitalWrite(RED_LED, HIGH);
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(BLUE_LED, LOW);
    break;
  case (YELLOW):
    digitalWrite(RED_LED, HIGH);
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(BLUE_LED, LOW);
    break;
  case (BLUE):
    digitalWrite(RED_LED, LOW);
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(BLUE_LED, HIGH);
    break;
  case (GREEN):
    digitalWrite(RED_LED, LOW);
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(BLUE_LED, LOW);
    break;
  }
}