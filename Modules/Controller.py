import time
import serial
import threading

class Controller:
    def __init__(self, port: str, baud: int = 115200):
        self.ser = serial.Serial(port, baud, timeout=1)

        self.seq = 0
        self.ack_lock = threading.Lock()
        self.last_ack = 0

        self._ack_thread = threading.Thread(
            target=self.read_acks,
            daemon=True
        )
        self._ack_thread.start()

    def read_acks(self):
        buf = b""
        while True:
            try:
                if self.ser.in_waiting:
                    buf += self.ser.read(self.ser.in_waiting)

                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.decode("ascii", errors="ignore").strip()

                        if line.startswith("ACK:"):
                            ack_seq = int(line[4:])
                            print("[RX ACK]", ack_seq)

                            with self.ack_lock:
                                self.last_ack = ack_seq

            except Exception as e:
                print("ACK reader error:", e)

            time.sleep(0.001)

    def send(self, line: str):
        self.seq += 1
        seq = self.seq
        timeout = 5.0

        print(line)

        payload = f"{seq}:{line}\n"
        self.ser.write(payload.encode("ascii"))

        t0 = time.time()
        while True:
            with self.ack_lock:
                if self.last_ack >= seq:
                    return True

            if time.time() - t0 > timeout:
                print("ACK TIMEOUT for seq", seq, line)
                return False

            time.sleep(0.001)

    def tap(self, idx: int, press_s: float = 0.05, gap_s: float = 0.05):
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
        self.send(f"HAT RELEASE")

    def close(self):
        self.ser.close()
