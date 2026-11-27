import io
import time
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

import serial

from radar_viewer import Viewer
from serial_monitor import HISTORY_BYTES, escaped
from session import HEADER
from test_viewer import packet


class MonitorTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = Viewer(self.root)
        self.addCleanup(self.app.close)
        self.root.update_idletasks()
        self.mon = self.app.monitor
        self.now = time.monotonic()

    def text(self):
        return self.mon.text.get('1.0', 'end-1c')

    def select(self):
        self.app.nav.select(self.app.monitor_tab)
        self.root.update()
        self.assertTrue(self.mon.text.winfo_ismapped())

    def connect(self):
        port = serial.serial_for_url('loop://', timeout=0)
        self.addCleanup(port.close)
        self.app.port.set('TEST-LOOP')
        with patch('radar_viewer.serial.Serial', return_value=port) as factory:
            self.app.connect()
            factory.assert_called_once_with('TEST-LOOP', 115200, timeout=0)
        return port

    def poll(self, port, data):
        port.write(data)
        self.now += 0.2
        self.app.poll(self.now)

    def control(self, caption):
        return next(w for w in self.app.monitor_tab.winfo_children() if w.cget('text') == caption)

    def test_loopback_capture_freeze_clear_partial_and_copy_selection(self):
        port = self.connect()
        raw = packet()
        self.poll(port, b'boot\r\n{bad}\n\x00\xff\x1b\\xff\n' + raw[:11])
        self.assertEqual(self.text(), '')  # hidden tab does no Tk text writes
        self.select()
        expected = 'boot\\x0d\n{bad}\n\\x00\\xff\\x1b\\\\xff\n' + raw[:11].decode()
        self.assertEqual(self.text(), expected)
        self.assertIn('TEST-LOOP', self.mon.label.cget('text'))
        self.mon.text.tag_add('sel', '1.0', '1.4')
        self.mon.text.event_generate('<<Copy>>')
        self.assertEqual(self.root.clipboard_get(), 'boot')
        freeze = self.control('Freeze monitor')
        freeze.invoke()
        self.app.recording = Mock()
        self.poll(port, raw[11:] + b'\npart')
        self.assertEqual(self.text(), expected)
        self.assertEqual(self.app.frames, 1)
        self.app.recording.append.assert_called_once()
        freeze.invoke()
        self.assertTrue(self.text().endswith(raw.decode() + '\npart'))
        self.poll(port, b'ial\n'+raw[:10])
        self.assertTrue(self.text().endswith('partial\n'+raw[:10].decode()))
        self.control('Clear').invoke()
        self.assertEqual(self.text(), '')
        self.poll(port, raw[10:] + b'\n')
        self.assertEqual(self.app.frames, 2)  # clear did not reset the parser
        self.assertEqual(self.text(), raw[10:].decode() + '\n')
        self.app.stop()
        self.assertIn('Last RX: TEST-LOOP', self.mon.label.cget('text'))
        self.assertEqual(self.text(), raw[10:].decode() + '\n')

    def test_bounded_tail_overflow_and_throttle(self):
        self.select()
        data = bytes(range(256)) * (HISTORY_BYTES // 256 + 2)
        self.mon.feed(data)
        self.mon.render(self.now)
        self.assertEqual(len(self.mon.buffer), HISTORY_BYTES)
        self.assertEqual(self.text(), escaped(data[-HISTORY_BYTES:]))
        self.mon.feed(b'end')
        self.mon.render(self.now + .001)
        self.assertFalse(self.text().endswith('end'))
        self.mon.render(self.now + .2)
        self.assertEqual(self.text(), escaped((data+b'end')[-HISTORY_BYTES:]))
        self.assertIn('515 older bytes discarded', self.mon.label.cget('text'))
        self.mon.feed(b'\x00' * (2*HISTORY_BYTES))  # no LF and no overlapping history
        self.mon.render(self.now + .4)
        self.assertEqual(self.text(), '\\x00' * HISTORY_BYTES)

    def test_demo_and_replay_never_feed_monitor(self):
        self.select()
        port = self.connect()
        self.poll(port, b'old boot')
        self.app.stop()
        self.app.demo()
        self.app.poll(self.now + .3)
        self.assertEqual(self.app.frames, 1)
        self.assertEqual(self.text(), '')
        self.assertIn('No serial input', self.mon.label.cget('text'))
        self.app.stop()
        with patch('radar_viewer.filedialog.askopenfilename', return_value='test.radar'), patch('builtins.open', return_value=io.BytesIO(HEADER + b'0\t' + packet() + b'\n')):
            self.app.replay()
        self.app.poll(self.app.start + .1)
        self.assertEqual(self.app.frames, 1)
        self.assertEqual(self.text(), '')
        self.assertIn('Replay · No serial input', self.mon.label.cget('text'))
