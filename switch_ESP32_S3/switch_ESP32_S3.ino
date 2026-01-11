#include <Arduino.h>
#include <switch_ESP32.h>

NSGamepad Gamepad;

HardwareSerial &CMD = Serial0;
#define DEBUG Serial

static char inBuf[256];
static size_t inLen = 0;

bool btnState[16] = { false };
uint8_t lx = 128, ly = 128;
uint8_t rx = 128, ry = 128;
uint8_t dpadDir = NSGAMEPAD_DPAD_CENTERED;

static void pumpDelay(uint32_t ms) {
  uint32_t start = millis();
  while (millis() - start < ms) {
    Gamepad.loop();
    delay(1);
  }
}

static inline void applyState() {
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

static void handleBtn(int idx, const char *action) {
  if (idx < 0 || idx > 15) return;

  if (!strcmp(action, "TAP")) {
    btnState[idx] = true;
    applyState();
    pumpDelay(50);
    btnState[idx] = false;
    applyState();
  } else if (!strcmp(action, "DOWN")) {
    btnState[idx] = true;
    applyState();
  } else if (!strcmp(action, "UP")) {
    btnState[idx] = false;
    applyState();
  }
}

static void handleStick(const char *which, int x, int y) {
  x = constrain(x, 0, 255);
  y = constrain(y, 0, 255);

  if (!strcmp(which, "L")) {
    lx = (uint8_t)x;
    ly = (uint8_t)y;
  } else if (!strcmp(which, "R")) {
    rx = (uint8_t)x;
    ry = (uint8_t)y;
  }

  applyState();
}

static void handleHatCmd(char *rest) {
  while (*rest == ' ') rest++;

  char *op = strtok(rest, " ");
  if (!op) return;

  for (char *p = op; *p; ++p) *p = toupper(*p);

  if (!strcmp(op, "RELEASE")) {
    dpad_release();
    return;
  }

  if (!strcmp(op, "HOLD") || !strcmp(op, "SET")) {
    char *arg = strtok(nullptr, " ");
    if (!arg) return;
    dpad_hold((uint8_t)atoi(arg));
    return;
  }

  if (!strcmp(op, "TAP")) {
    char *arg1 = strtok(nullptr, " ");
    char *arg2 = strtok(nullptr, " ");
    if (!arg1 || !arg2) return;

    int dir = atoi(arg1);
    int ms = atoi(arg2);
    ms = constrain(ms, 10, 5000);

    dpad_hold((uint8_t)dir);
    pumpDelay((uint32_t)ms);
    dpad_release();
    return;
  }

  int dir = atoi(op);
  dpad_hold((uint8_t)dir);
}

static void handleCommandLine(char *line) {
  while (*line == ' ') line++;
  if (!*line) return;

  char *cmdLine = line;

  char *colon = strchr(line, ':');
  if (colon) {
    cmdLine = colon + 1;
    while (*cmdLine == ' ') cmdLine++;
  }

  char *cmd = strtok(cmdLine, " ");
  if (!cmd) return;

  if (!strcmp(cmd, "BTN")) {
    char *idxStr = strtok(nullptr, " ");
    char *action = strtok(nullptr, " ");
    if (!idxStr || !action) return;
    handleBtn(atoi(idxStr), action);
  } else if (!strcmp(cmd, "STICK")) {
    char *which = strtok(nullptr, " ");
    char *xStr  = strtok(nullptr, " ");
    char *yStr  = strtok(nullptr, " ");
    if (!which || !xStr || !yStr) return;
    handleStick(which, atoi(xStr), atoi(yStr));
  } else if (!strcmp(cmd, "HAT")) {
    char tmp[64];
    tmp[0] = 0;

    char *op = strtok(nullptr, " ");
    if (!op) return;
    strncat(tmp, op, sizeof(tmp) - 1);

    char *a1 = strtok(nullptr, " ");
    char *a2 = strtok(nullptr, " ");
    if (a1) { strncat(tmp, " ", sizeof(tmp) - strlen(tmp) - 1); strncat(tmp, a1, sizeof(tmp) - strlen(tmp) - 1); }
    if (a2) { strncat(tmp, " ", sizeof(tmp) - strlen(tmp) - 1); strncat(tmp, a2, sizeof(tmp) - strlen(tmp) - 1); }

    handleHatCmd(tmp);
  }
}

void setup() {
  DEBUG.begin(115200);
  pumpDelay(500);

  CMD.begin(115200);

  USB.begin();
  Gamepad.begin();
  applyState();
}

void loop() {
  while (CMD.available() > 0) {
    char c = (char)CMD.read();

    if (c == '\n' || c == '\r') {
      if (inLen > 0) {
        inBuf[inLen] = '\0';
        handleCommandLine(inBuf);
        inLen = 0;
      }
      continue;
    }

    if (inLen + 1 < sizeof(inBuf)) {
      inBuf[inLen++] = c;
    } else {
      inLen = 0;
    }
  }

  Gamepad.loop();
}
