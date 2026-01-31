import socket
import threading
import logging

class RossTalkClient:
    def __init__(self, host: str, port: int, timeout: float = 1.5, dry_run: bool = False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.dry_run = dry_run
        self.lock = threading.Lock()

    def send(self, command: str) -> bool:
        cmd = command.strip()

        if self.dry_run:
            # In dry run mode, just log at INFO level instead of sending
            logging.info("RossTalk [DRY RUN] → %s:%d: %s", self.host, self.port, cmd)
            return True

        data = (cmd + "\r\n").encode("ascii", errors="ignore")
        logging.debug("RossTalk → %s:%d: %s", self.host, self.port, cmd)
        try:
            with self.lock:
                with socket.create_connection((self.host, self.port), self.timeout) as s:
                    s.sendall(data)
            return True
        except Exception as e:
            logging.error("RossTalk error: %s", e)
            return False

    def healthy(self) -> bool:
        if self.dry_run:
            # In dry run mode, always report as healthy
            return True

        try:
            with socket.create_connection((self.host, self.port), self.timeout):
                return True
        except Exception:
            return False
