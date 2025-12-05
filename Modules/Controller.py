import time
import serial
from threading import Lock

class Controller:
    def __init__(self, port: str, baud: 115200):
        self.ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)
    
    def send(self, line:str):
        self.ser.write((line + "\n").encode("ascii"))
        self.ser.flush()

    def tap(self, idx: int, press_s: float = 0.05, gap_s = 0.05):
        self.send(f"BTN {idx} TAP")
        time.sleep(press_s+gap_s)

    def down(self, idx: int):
        self.send(f"BTN {idx} DOWN")

    def up(self, idx: int):
        self.send(f"BTN {idx} UP")

    def hold(self, idx: int, duration_s: float):
        self.down(idx)
        time.sleep(duration_s)
        self.up(idx)
    
    def stick(self, which: str, x: int, y: int, duration_s: float = 0.0, center: bool = True):
        self.send(f"STICK {which} {x} {x}")
        if duration_s > 0:
            time.sleep(duration_s)
        if center:
            self.send(f"STICK {which} 128 128")

    def dpad(self, dir: int, duration_s: float = 0.0):
        self.send(f"HAT {dir}")
        if duration_s > 0:
            time.sleep(duration_s)
            self.send("HAT 8")

    def close(self):
        self.ser.close()