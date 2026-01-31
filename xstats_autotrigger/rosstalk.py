import socket
import threading
import logging

class RossTalkClient:
    def __init__(self, host: str, port: int, timeout: float = 1.5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.lock = threading.Lock()

    def send(self, command: str) -> bool:
        data = (command.strip() + "\r\n").encode("ascii", errors="ignore")
        logging.debug("RossTalk → %s:%d: %s", self.host, self.port, command.strip())
        try:
            with self.lock:
                with socket.create_connection((self.host, self.port), self.timeout) as s:
                    s.sendall(data)
            return True
        except Exception as e:
            logging.error("RossTalk error: %s", e)
            return False

    def healthy(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), self.timeout):
                return True
        except Exception:
            return False
