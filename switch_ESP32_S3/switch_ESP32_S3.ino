#include <Arduino.h>
#include <switch_ESP32.h>

NSGamepad Gamepad;

// command port = UART (to your "UART cable")
HardwareSerial &CMD = Serial0;

// debug port = USB CDC (to your "USB cable")
#define DEBUG Serial

String inLine;

// --- internal state ---
bool    btnState[16] = {false};
uint8_t lx = 128, ly = 128;
uint8_t rx = 128, ry = 128;
uint8_t dpadDir = NSGAMEPAD_DPAD_CENTERED;

void applyState() {
  Gamepad.releaseAll();
  for (int i = 0; i < 16; ++i) {
    if (btnState[i]) {
      Gamepad.press(i);
    }
  }

  Gamepad.leftXAxis(lx);
  Gamepad.leftYAxis(ly);
  Gamepad.rightXAxis(rx);
  Gamepad.rightYAxis(ry);

  Gamepad.dPad((NSDirection_t)dpadDir);

  Gamepad.write();
}

void handleBtn(int idx, const String &action) {
  if (idx < 0 || idx > 15) return;

  if (action == "TAP") {
    btnState[idx] = true;
    applyState();
    delay(50);
    btnState[idx] = false;
    applyState();
  } else if (action == "DOWN") {
    btnState[idx] = true;
    applyState();
  } else if (action == "UP") {
    btnState[idx] = false;
    applyState();
  }
}

void handleStick(const String &which, int x, int y) {
  x = constrain(x, 0, 255);
  y = constrain(y, 0, 255);

  if (which == "L") {
    lx = x; ly = y;
  } else if (which == "R") {
    rx = x; ry = y;
  }

  applyState();
}

void handleHat(int dir) {
  if (dir >= 0 && dir <= 7) {
    dpadDir = (uint8_t)dir;
  } else {
    dpadDir = NSGAMEPAD_DPAD_CENTERED;
  }
  applyState();
}

void handleCommand(String line) {
  line.trim();
  if (!line.length()) return;

  DEBUG.print("RAW: ");
  DEBUG.println(line);

  int colonIndex = line.indexOf(':');
  if (colonIndex < 0) return;  // invalid format

  int seq = line.substring(0, colonIndex).toInt();
  String cmdLine = line.substring(colonIndex + 1);

  DEBUG.print("SEQ: ");
  DEBUG.println(seq);

  int s1 = cmdLine.indexOf(' ');
  if (s1 < 0) return;

  String cmd  = cmdLine.substring(0, s1);
  String rest = cmdLine.substring(s1 + 1);

  if (cmd == "BTN") {
    int s2 = rest.indexOf(' ');
    if (s2 < 0) return;
    int idx = rest.substring(0, s2).toInt();
    String action = rest.substring(s2 + 1);

    DEBUG.print("BTN "); DEBUG.print(idx);
    DEBUG.print(" "); DEBUG.println(action);

    handleBtn(idx, action);

  } 
  else if (cmd == "STICK") {
    int s2 = rest.indexOf(' ');
    if (s2 < 0) return;
    String which = rest.substring(0, s2);
    String nums  = rest.substring(s2 + 1);
    int s3 = nums.indexOf(' ');
    if (s3 < 0) return;
    int x = nums.substring(0, s3).toInt();
    int y = nums.substring(s3 + 1).toInt();
    handleStick(which, x, y);

  } 
  else if (cmd == "HAT") {
    int dir = rest.toInt();
    handleHat(dir);
  }

CMD.print("ACK:");
CMD.println(seq);

DEBUG.print("ACK:");
DEBUG.println(seq);

}

void setup() {
  DEBUG.begin(115200);     // USB CDC debug (optional)
  delay(1000);
  DEBUG.println("NSGamepad + UART command mode");

  CMD.begin(115200);       // UART0: commands from PC on UART cable
  Gamepad.begin();
}

void loop() {
  while (CMD.available() > 0) {
    char c = CMD.read();
    if (c == '\n' || c == '\r') {
      if (inLine.length() > 0) {
        handleCommand(inLine);
        inLine = "";
      }
    } else {
      inLine += c;
    }
  }

  // If needed: Gamepad.loop();
}
