"""Session rows preserve the packet bytes and add a monotonic host arrival offset."""
from protocol import MAX_LINE, decode

HEADER = b'FYP-RADAR-SESSION 1\n'


class Recorder:
    def __init__(self, path, now):
        self.start = now
        self.file = open(path, 'wb')
        try:
            self.file.write(HEADER)
        except OSError:
            self.file.close()
            raise

    def append(self, raw, now):
        ms = int((now - self.start) * 1000)
        self.file.write(str(ms).encode('ascii') + b'\t' + raw + b'\n')
        self.file.flush()

    def close(self):
        self.file.close()


class Replay:
    def __init__(self, path, now):
        self.file = open(path, 'rb')
        self.start = now
        self.last_ms = 0
        self.row = 1
        self.next = None
        try:
            if self.file.readline(len(HEADER) + 1) != HEADER:
                raise ValueError('not a FYP radar session v1')
            self.advance()
            if self.next is None:
                raise ValueError('empty session')
        except (OSError, ValueError):
            self.close()
            raise

    def advance(self):
        data = self.file.readline(MAX_LINE + 24)
        self.row += 1
        if not data:
            self.next = None
            return
        try:
            if not data.endswith(b'\n'):
                raise ValueError('truncated or oversized row')
            stamp, raw = data[:-1].split(b'\t', 1)
            if not stamp.isdigit() or len(stamp) > 20 or int(stamp) < self.last_ms:
                raise ValueError('invalid arrival offset')
            self.last_ms = int(stamp)
            self.next = decode(raw)
        except ValueError as exc:
            raise ValueError(f'session line {self.row}: {exc}') from exc

    def due(self, now):
        return self.next is not None and self.last_ms <= (now - self.start) * 1000

    def close(self):
        self.file.close()
