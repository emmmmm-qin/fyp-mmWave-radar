import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from protocol import decode, LineReader, MAX_LINE
from session import HEADER, Recorder, Replay


# The same two-point native fixture, in each wire format (including LF).
CLOUD_V1 = (b'{"protocol":"fyp-radar","v":1,"source":"radar","seq":42,"t_ms":5300,'
            b'"state":"cloud","points":[[-1,2,-1.5],[0,0,16383.5]]}\n')
CLOUD_V2 = b'R2,radar,42,5300,cloud,-1,2,-1.5,0,0,16383.5\n'


class WireTest(unittest.TestCase):
    def test_fixture(self):
        self.assertEqual(decode(CLOUD_V2), dict(json.loads(CLOUD_V1), v=2))

    def test_boundaries(self):
        prefix = b'R2,demo,4294967295,18446744073709551615,'
        for state in (b'unavailable', b'no_cloud'):
            self.assertEqual(decode(prefix + state)['points'], [])
        p = decode(prefix + b'cloud' + b',-0,1e-45,-3.40282347e+38' * 100)
        self.assertEqual((p['seq'], p['t_ms'], len(p['points'])), (2**32-1, 2**64-1, 100))
        self.assertEqual(math.copysign(1, p['points'][99][0]), -1)
        self.assertEqual(p['points'][99][1:], [1e-45, -3.40282347e38])

    def test_invalid_v2(self):
        for body in (b'demo,1,1', b'unknown,1,1,no_cloud', b'demo,1,1,bad',
                     b'demo,-1,1,no_cloud', b'demo,+1,1,no_cloud', b'demo,4294967296,1,no_cloud',
                     b'demo,1,18446744073709551616,no_cloud', b'demo,1,1.0,no_cloud',
                     b'demo,1,1,no_cloud,', b'demo,1,1,unavailable,1,2,3', b'demo,1,1,cloud',
                     b'demo,1,1,cloud,1,2', b'demo,1,1,cloud,1,2,3,',
                     b'demo,1,1,cloud' + b',0,0,0'*101):
            with self.subTest(body=body), self.assertRaises(ValueError):
                decode(b'R2,' + body)
        for token in (b'nan', b'inf', b'1e309', b'1_2', b' 1', b'1\t', b'', b'\xff'):
            with self.subTest(token=token), self.assertRaises(ValueError):
                decode(b'R2,radar,2,4,cloud,1,2,' + token)

    def test_legacy_bounds(self):
        for changes in (dict(t_ms=2**64), dict(points=[]), dict(t_ms=2**80, points=[])):
            expected = dict(json.loads(CLOUD_V1), **changes)
            with self.subTest(changes=changes):
                self.assertEqual(decode(json.dumps(expected).encode('ascii')), expected)

    def test_fragmented_recording_and_replay(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'capture'
            reader = LineReader()
            rec = Recorder(path, 1)
            data = b'boot banner\r\n' + CLOUD_V1 + CLOUD_V2
            events = [e for byte in data for e in reader.feed(bytes([byte]))]
            try:
                for i, ((packet, raw), error) in enumerate(events):
                    self.assertIsNone(error)
                    self.assertEqual(packet['v'], i + 1)
                    rec.append(raw, 1 + i)
            finally:
                rec.close()
            self.assertEqual(path.read_bytes(), HEADER + b'0\t' + CLOUD_V1 + b'1000\t' + CLOUD_V2)
            replay = Replay(path, 5)
            try:
                self.assertEqual(replay.next, decode(CLOUD_V1))
                replay.advance()
                self.assertFalse(replay.due(5.5))
                self.assertTrue(replay.due(6))
                self.assertEqual(replay.next, decode(CLOUD_V2))
                replay.advance()
                self.assertIsNone(replay.next)
            finally:
                replay.close()

    def test_overflow_and_bad_frame_resync(self):
        reader = LineReader()
        events = list(reader.feed(b'R2,' + b'x'*MAX_LINE + CLOUD_V2 + b'R2,bad\n' + CLOUD_V2))
        self.assertEqual(len(events), 3)
        self.assertTrue(events[0][1] and events[1][1])
        self.assertEqual(events[2], ((decode(CLOUD_V2), CLOUD_V2[:-1]), None))
