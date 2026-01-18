import time
import serial
import threading

class Controller:
    def __init__(self, port: str, baud: int = 115200):
        # No ACK reader, no seq/ack state.
        # Keep timeouts so dead ports don't hang forever.
        self.ser = serial.Serial(port, baud, timeout=0.1, write_timeout=0.2)

    def send(self, line: str) -> bool:
        """
        Fire-and-forget send. Returns False on write failure.
        """
        try:
            payload = f"{line}\n"
            self.ser.write(payload.encode("ascii"))
            return True
        except Exception as e:
            print("SERIAL send error:", e)
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
        self.send(f"STICK {which} {x} {y}")
        if duration_s > 0:
            time.sleep(duration_s)
        if center:
            self.send(f"STICK {which} 128 128")

    def dpad(self, dir: int, duration_s: float = 0.0):
        self.send(f"HAT {dir}")
        if duration_s > 0:
            time.sleep(duration_s)
            self.send("HAT 8")

    def dpad_down(self, dir: int):
        self.send(f"HAT HOLD {dir}")

    def dpad_up(self):
        self.send("HAT RELEASE")

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

