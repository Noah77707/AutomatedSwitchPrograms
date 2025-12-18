#include <Arduino.h>
#include <switch_ESP32.h>

NSGamepad Gamepad;

HardwareSerial &CMD = Serial0;
#define DEBUG Serial

String inLine;

// --- latched state ---
bool btnState[16] = { false };
uint8_t lx = 128, ly = 128;
uint8_t rx = 128, ry = 128;
uint8_t dpadDir = NSGAMEPAD_DPAD_CENTERED;

static void pumpDelay(uint32_t ms) {
  uint32_t start = millis();
  while (millis() - start < ms) {
    Gamepad.loop();     // keep USB alive
    delay(1);
  }
}

static inline void applyState() {
  // IMPORTANT: do not releaseAll() or you'll break holds.
  // Set buttons to match btnState.
  for (int i = 0; i < 16; ++i) {
    if (btnState[i]) Gamepad.press(i);
    else Gamepad.release(i);
  }

  Gamepad.leftXAxis(lx);
  Gamepad.leftYAxis(ly);
  Gamepad.rightXAxis(rx);
  Gamepad.rightYAxis(ry);

  Gamepad.dPad((NSDirection_t)dpadDir);
  Gamepad.write();
}

static inline void dpad_hold(uint8_t dir) {
  if (dir <= 7) dpadDir = dir;
  else dpadDir = NSGAMEPAD_DPAD_CENTERED;
  applyState();
}

static inline void dpad_release() {
  dpadDir = NSGAMEPAD_DPAD_CENTERED;
  applyState();
}

void handleBtn(int idx, const String &action) {
  if (idx < 0 || idx > 15) return;

  if (action == "TAP") {
    btnState[idx] = true;
    applyState();
    pumpDelay(50);
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
    lx = x;
    ly = y;
  } else if (which == "R") {
    rx = x;
    ry = y;
  }

  applyState();
}

void handleHatCmd(const String &rest) {
  // Supported:
  // HAT HOLD <dir>
  // HAT RELEASE
  // HAT SET <dir>          (backwards compatible)
  // HAT TAP <dir> <ms>
  String r = rest;
  r.trim();

  int s1 = r.indexOf(' ');
  String op = (s1 < 0) ? r : r.substring(0, s1);
  String args = (s1 < 0) ? "" : r.substring(s1 + 1);
  op.toUpperCase();
  args.trim();

  if (op == "RELEASE") {
    dpad_release();
    return;
  }

  if (op == "HOLD" || op == "SET") {
    int dir = args.toInt();
    dpad_hold((uint8_t)dir);
    return;
  }

  if (op == "TAP") {
    int s2 = args.indexOf(' ');
    if (s2 < 0) return;
    int dir = args.substring(0, s2).toInt();
    int ms = args.substring(s2 + 1).toInt();
    ms = constrain(ms, 10, 5000);

    dpad_hold((uint8_t)dir);
    pumpDelay(ms);
    dpad_release();
    return;
  }

  // Old behavior: HAT <dir>
  int dir = r.toInt();
  dpad_hold((uint8_t)dir);
}

void handleCommand(String line) {
  line.trim();
  if (!line.length()) return;

  int colonIndex = line.indexOf(':');
  if (colonIndex < 0) return;

  int seq = line.substring(0, colonIndex).toInt();
  String cmdLine = line.substring(colonIndex + 1);
  cmdLine.trim();

  int s1 = cmdLine.indexOf(' ');
  if (s1 < 0) return;

  String cmd = cmdLine.substring(0, s1);
  String rest = cmdLine.substring(s1 + 1);
  cmd.trim();
  rest.trim();

  if (cmd == "BTN") {
    int s2 = rest.indexOf(' ');
    if (s2 < 0) return;
    int idx = rest.substring(0, s2).toInt();
    String action = rest.substring(s2 + 1);
    handleBtn(idx, action);
  } else if (cmd == "STICK") {
    int s2 = rest.indexOf(' ');
    if (s2 < 0) return;
    String which = rest.substring(0, s2);
    String nums = rest.substring(s2 + 1);
    int s3 = nums.indexOf(' ');
    if (s3 < 0) return;
    int x = nums.substring(0, s3).toInt();
    int y = nums.substring(s3 + 1).toInt();
    handleStick(which, x, y);
  } else if (cmd == "HAT") {
    handleHatCmd(rest);
  }

  CMD.print("ACK:");
  CMD.println(seq);
}

void setup() {
  DEBUG.begin(115200);
  pumpDelay(1000);
  CMD.begin(115200);
  USB.begin();
  Gamepad.begin();
  applyState();
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
  
}
