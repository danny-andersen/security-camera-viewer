#define VSENSE_IN 0     // Connected to TV USB output - high when TV is on, low when off
#define PICONTROL_OUT 1 // Tells the raspberry pi whether to shutdown or not. Must be high when the PI boots. Driving it low tells the PI to shutdown immediately
#define RELAY_OUT 2     // Controls the power to the PI
#define RED_LED 3    
#define GREEN_LED 4

const int LOOP_DELAY = 1000; // 10 sec loop time
const int BOOT_DELAY = 1200000; // 2 mins boot up time
const int SHUTDOWN_DELAY = 1200000; // 2 mins shutdown time

enum Colours {
  OFF,
  RED,
  YELLOW,
  GREEN,
};

enum State {
  INIT,
  TV_OFF,
  TV_ON,
  POWER_ON_PI,
  POWER_OFF_PI,
};

int state = INIT;
int newState = state;

void setup() {
  pinMode(PICONTROL_OUT, OUTPUT);     
  pinMode(RED_LED, OUTPUT);     // Initialize the LED_BUILTIN pin as an output
  pinMode(GREEN_LED, OUTPUT);     // Initialize the LED_BUILTIN pin as an output
  pinMode(RELAY_OUT, OUTPUT);     // Initialize the LED_BUILTIN pin as an output

  digitalWrite(PICONTROL_OUT, LOW);
  digitalWrite(RELAY_OUT, LOW);
  setLED(RED);
}

void loop() {
  int tvState = digitalRead(VSENSE_IN);
  int delayTime = LOOP_DELAY;
  switch (state) {
    case(INIT):
      if (tvState == HIGH) {
        newState = POWER_ON_PI;
      } else {
        newState = TV_OFF;
      }
      break;
    case(POWER_ON_PI):
      digitalWrite(PICONTROL_OUT, HIGH);
      digitalWrite(RELAY_OUT, HIGH);
      setLED(YELLOW);
      newState = TV_ON;
      delayTime = BOOT_DELAY;
      break;
    case(TV_ON):
      if (tvState == LOW) {
        newState = POWER_OFF_PI;
      }
      break;
    case(POWER_OFF_PI):
      digitalWrite(PICONTROL_OUT, LOW);
      setLED(YELLOW);
      delayTime = SHUTDOWN_DELAY;
      newState = TV_OFF;
      break;
    case(TV_OFF):
      if (tvState == HIGH) {
        newState = POWER_ON_PI;
      }
      break;
  }

  delay(delayTime);

  if (state == POWER_ON_PI && newState == TV_ON) {
    setLED(GREEN);
  }
  if (state == POWER_OFF_PI && newState == TV_OFF) {
    setLED(RED);
  }
  state = newState;
}

void setLED(Colours colour) {
  switch (colour) {
    case (OFF):
      digitalWrite(RED_LED, LOW);
      digitalWrite(GREEN_LED, LOW);
      break;
    case (RED):
      digitalWrite(RED_LED, HIGH);
      digitalWrite(GREEN_LED, LOW);
      break;
    case (YELLOW):
      digitalWrite(RED_LED, HIGH);
      digitalWrite(GREEN_LED, HIGH);
      break;
    case (GREEN):
      digitalWrite(RED_LED, LOW);
      digitalWrite(GREEN_LED, HIGH);
      break;
  }
}