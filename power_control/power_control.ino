#define VSENSE_IN 3     // Connected to TV USB output - high when TV is on, low when off
#define PICONTROL_OUT 4 // Tells the raspberry pi whether to shutdown or not. Must be high when the PI boots. Driving it low tells the PI to shutdown immediately
#define RELAY_OUT 5     // Controls the power to the PI
#define RED_LED 6    
#define GREEN_LED 7
#define BLUE_LED 8
#define RELAY_ON LOW    //Relay is low level triggered
#define RELAY_OFF HIGH
#define TV_IS_ON LOW //When TV is on, this line is driven low
#define TV_IS_OFF HIGH //When TV is off, this line is pulled high

const unsigned long LOOP_DELAY = 1000; // 10 sec loop time
const unsigned long BOOT_DELAY = 300000; // 5 mins boot up and settle time - minimum on period - will not enter a power off cycle until this has elapsed
const unsigned long SHUTDOWN_DELAY = 120000; // 2 mins shutdown time


enum Colours {
  OFF,
  RED,
  YELLOW,
  GREEN,
  BLUE,
};

enum State {
  INIT,
  TV_OFF,
  TV_ON,
  POWER_ON_PI,
  POWER_OFF_PI,
};

#define IDNAME(name) #name
const char* stateNames[] = {IDNAME(INIT), IDNAME(TV_OFF), IDNAME(TV_ON), IDNAME(POWER_ON_PI), IDNAME(POWER_OFF_PI)};

int state = INIT;
int newState = state;

void setup() {
  Serial.begin(38400);
  pinMode(VSENSE_IN, INPUT_PULLUP);     
  pinMode(PICONTROL_OUT, OUTPUT);     
  pinMode(RED_LED, OUTPUT);     // Initialize the LED_BUILTIN pin as an output
  pinMode(GREEN_LED, OUTPUT);     // Initialize the LED_BUILTIN pin as an output
  pinMode(BLUE_LED, OUTPUT);     // Initialize the LED_BUILTIN pin as an output
  pinMode(RELAY_OUT, OUTPUT);     // Initialize the LED_BUILTIN pin as an output

  digitalWrite(PICONTROL_OUT, LOW);
  digitalWrite(RELAY_OUT, RELAY_OFF);
  setLED(RED);
}

void loop() {
  int tvState = digitalRead(VSENSE_IN);
  // Serial.print("State: ");
  // Serial.print(stateNames[state]);
  // Serial.print(" , TV is ");
  // Serial.println(tvState);
  unsigned long delayTime = LOOP_DELAY;
  switch (state) {
    case(INIT):
      if (tvState == TV_IS_ON) {
        newState = POWER_ON_PI;
      } else {
        newState = TV_OFF;
      }
      break;
    case(POWER_ON_PI):
      digitalWrite(PICONTROL_OUT, LOW);
      digitalWrite(RELAY_OUT, RELAY_ON);
      setLED(BLUE);
      newState = TV_ON;
      delayTime = BOOT_DELAY;
      break;
    case(TV_ON):
      if (tvState == TV_IS_OFF) {
        newState = POWER_OFF_PI;
      }
      break;
    case(POWER_OFF_PI):
      digitalWrite(PICONTROL_OUT, HIGH);
      setLED(YELLOW);
      delayTime = SHUTDOWN_DELAY;
      newState = TV_OFF;
      break;
    case(TV_OFF):
      if (tvState == TV_IS_ON) {
        newState = POWER_ON_PI;
      }
      break;
  }
  // Serial.print("New State: ");
  // Serial.print(stateNames[newState]);
  // Serial.println(" Sleeping..");

  delay(delayTime);

  if (state == POWER_ON_PI && newState == TV_ON) {
    setLED(GREEN);
  }
  if (state == POWER_OFF_PI && newState == TV_OFF) {
    digitalWrite(RELAY_OUT, RELAY_OFF);
    delay(5000); //Ensure PI is powercycled
    setLED(RED);
  }
  state = newState;
}

void setLED(Colours colour) {
  // Serial.print("Setting colour to ");
  // Serial.println(colour);
  switch (colour) {
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