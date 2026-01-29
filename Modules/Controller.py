import time
import serial

class Controller:

    def __init__(self, port: str | None = None, baud: int = 115200):
        self.baud = int(baud)
        self.ser: serial.Serial | None = None
        self.is_open = False
        self._last_send_err_t = 0.0

        if port:
            self.connect(port)

    def connect(self, port: str) -> None:
        port = (port or "").strip()
        if not port:
            return

        self.close()

        # Keep timeouts so dead ports do not hang forever.
        self.ser = serial.Serial(
            port,
            self.baud,
            timeout=0.1,
            write_timeout=0.2,
        )
        self.is_open = True

    def close(self) -> None:
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.is_open = False

    def send(self, line: str) -> bool:
        if not self.is_open or self.ser is None:
            # throttle spam
            now = time.monotonic()
            if now - self._last_send_err_t > 1.0:
                self._last_send_err_t = now
                print("SERIAL send error: Attempting to use a port that is not open")
            return False

        try:
            payload = f"{line}\n"
            self.ser.write(payload.encode("ascii", errors="ignore"))
            return True
        except Exception as e:
            now = time.monotonic()
            if now - self._last_send_err_t > 1.0:
                self._last_send_err_t = now
                print("SERIAL send error:", e)
            # treat as disconnected if the port died
            return False

    def tap(self, idx: int, press_s: float = 0.05, gap_s: float = 0.2):
        self.send(f"BTN {idx} TAP")
        time.sleep(press_s + gap_s)

    def down(self, idx: int):
        self.send(f"BTN {idx} DOWN")

    def up(self, idx: int):
        self.send(f"BTN {idx} UP")

    def hold(self, idx: int, duration_s: float):
        self.down(idx)
        time.sleep(duration_s)
        self.up(idx)

    def stick(self, which: str, x: int, y: int, duration_s: float = 0.0, center: bool = True):
        """
        X, Y: 0, 0 = Left, Down
        X, Y: 256, 256 = Right, Up
        """
        self.send(f"STICK {which} {int(x)} {int(y)}")
        if duration_s > 0:
            time.sleep(duration_s)
        if center:
            self.send(f"STICK {which} 128 128")

    def stick_up(self, which: str, duration_s: float = 0.0, center: bool = True):
        self.stick(which, "128", "0", duration_s, center)
    
    def stick_down(self, which: str, duration_s: float = 0.0, center: bool = True):
        self.stick(which, "128", "256", duration_s, center)
    
    def stick_left(self, which: str, duration_s: float = 0.0, center: bool = True):
        self.stick(which, "0", "128", duration_s, center)
    
    def stick_right(self, which: str, duration_s: float = 0.0, center: bool = True):
        self.stick(which, "256", "128", duration_s, center)
    
    def dpad(self, dir: int, duration_s: float = 0.05):
        self.send(f"HAT {int(dir)}")
        if duration_s > 0:
            time.sleep(duration_s)
            self.send("HAT 8")
    
    def dpad_down(self, dir: int):
        self.send(f"HAT HOLD {int(dir)}")

    def dpad_up(self):
        self.send("HAT RELEASE")
