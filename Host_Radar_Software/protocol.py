"""Decode the host protocol, not the radar's native binary UART format."""
import json
import math

MAX_LINE = 16384  # Bytes before LF, including an optional CR.
FIELDS = {'protocol', 'v', 'source', 'seq', 't_ms', 'state', 'points'}


def unique_object(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError('duplicate JSON field')
    return obj


def decode(line):
    if len(line) > MAX_LINE:
        raise ValueError('packet exceeds 16 KiB')
    try:
        p = json.loads(line.decode('ascii'), object_pairs_hook=unique_object)
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise ValueError(f'invalid ASCII JSON: {exc}') from exc
    if not isinstance(p, dict) or set(p) != FIELDS:
        raise ValueError('expected exactly the seven v1 packet fields')
    if p['protocol'] != 'fyp-radar' or type(p['v']) is not int or p['v'] != 1:
        raise ValueError('unsupported protocol or version')
    if p['source'] not in ('radar', 'demo') or p['state'] not in ('cloud', 'no_cloud', 'unavailable'):
        raise ValueError('unknown source or state')
    if type(p['seq']) is not int or not 0 <= p['seq'] <= 0xffffffff:
        raise ValueError('seq must be uint32')
    if type(p['t_ms']) is not int or p['t_ms'] < 0:
        raise ValueError('t_ms must be a nonnegative integer')
    points = p['points']
    if not isinstance(points, list) or len(points) > 100 or (p['state'] != 'cloud' and points):
        raise ValueError('invalid point count for packet state')
    for row in points:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError('each point must contain x, y and radial velocity')
        for n in row:
            try:
                if type(n) not in (int, float) or not math.isfinite(n):
                    raise ValueError('point coordinates and velocity must be finite numbers')
            except OverflowError as exc:
                raise ValueError('point outside numeric range') from exc
    return p


class LineReader:
    """Discard an overflowing line through LF, never interpret its tail as a packet."""
    def __init__(self):
        self.pending = bytearray()
        self.dropping = False

    def feed(self, chunk):
        parts = chunk.split(b'\n')
        for i, part in enumerate(parts):
            complete = i < len(parts) - 1
            if not self.dropping:
                if len(self.pending) + len(part) > MAX_LINE:
                    self.pending.clear()
                    self.dropping = True
                    yield None, 'line exceeds 16 KiB'
                else:
                    self.pending.extend(part)
            if complete:
                raw = bytes(self.pending)
                self.pending.clear()
                self.dropping = False
                # UART startup banners are not host packets.
                if raw.lstrip().startswith((b'{', b'[')):
                    try:
                        yield (decode(raw), raw), None
                    except ValueError as exc:
                        yield None, str(exc)
