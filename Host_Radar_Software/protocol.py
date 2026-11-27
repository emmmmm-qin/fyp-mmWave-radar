"""Decode the host protocol, not the radar's native binary UART format."""
import json
import math
import re

# Decimal syntax emitted by %.9g; exclude whitespace, NaN, hex and underscores.
DECIMAL = re.compile(rb'-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')

MAX_LINE = 16384  # Bytes before LF, including an optional CR.
FIELDS = {'protocol', 'v', 'source', 'seq', 't_ms', 'state', 'points'}


def unique_object(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError('duplicate JSON field')
    return obj


def decode_v2(line):
    fields = line.split(b',', 305)  # Five header fields and at most 300 coordinates.
    if not 5 <= len(fields) <= 305 or (len(fields) - 5) % 3:
        raise ValueError('expected v2 header and up to 100 complete triples')
    _, source, seq, uptime, state = fields[:5]
    if source not in (b'radar', b'demo') or state not in (b'cloud', b'no_cloud', b'unavailable'):
        raise ValueError('unknown source or state')
    if (state == b'cloud') != (len(fields) > 5):
        raise ValueError('invalid point count for packet state')
    if not seq.isdigit() or len(seq) > 10 or int(seq) > 0xffffffff:
        raise ValueError('seq must be uint32')
    if not uptime.isdigit() or len(uptime) > 20 or int(uptime) > 0xffffffffffffffff:
        raise ValueError('t_ms must be uint64')
    coords = []
    for field in fields[5:]:
        if not DECIMAL.fullmatch(field):
            raise ValueError('invalid decimal coordinate')
        value = float(field)
        if not math.isfinite(value):
            raise ValueError('nonfinite coordinate')
        coords.append(value)
    return dict(protocol='fyp-radar', v=2, source=source.decode('ascii'), seq=int(seq),
                t_ms=int(uptime), state=state.decode('ascii'),
                points=[coords[i:i+3] for i in range(0, len(coords), 3)])


def decode(line):
    line = line.removesuffix(b'\n')
    if len(line) > MAX_LINE:
        raise ValueError('packet exceeds 16 KiB')
    if line.startswith(b'R2,'):
        return decode_v2(line.removesuffix(b'\r'))
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
    # Historical v1 recordings allowed unbounded uptime and empty clouds.
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
                if raw.lstrip().startswith((b'{', b'[', b'R2,')):
                    try:
                        yield (decode(raw), raw), None
                    except ValueError as exc:
                        yield None, str(exc)
