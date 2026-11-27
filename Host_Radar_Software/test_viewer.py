import io
import json
import time
import tkinter as tk
import unittest
from unittest.mock import patch, Mock

import serial

from protocol import MAX_LINE, LineReader, decode
from radar_viewer import Viewer, READ_BYTES, STALE_SECONDS
from session import Recorder, Replay, HEADER


def packet(**changes):
    fields = dict(protocol='fyp-radar', v=1, source='radar', seq=1, t_ms=25,
                  state='cloud', points=[[0, 1.25, -0.5]])
    return json.dumps(dict(fields, **changes)).encode('ascii')


class ProtocolTest(unittest.TestCase):
    def test_valid_boundaries(self):
        for raw in (packet(seq=0xffffffff, points=[[1, 2, 3]]*100), packet(source='demo'),
                    packet(state='no_cloud', points=[]), packet(state='unavailable', points=[])):
            self.assertEqual(decode(raw), json.loads(raw))

    def test_invalid_fields(self):
        for changes in [dict(protocol='bad'), dict(v=True), dict(v=2), dict(source='live'),
                        dict(seq=-1), dict(seq=2**32), dict(seq=True), dict(t_ms=-1), dict(t_ms=1.1),
                        dict(state='bad'), dict(state='unavailable'), dict(state='no_cloud'), dict(extra=2),
                        dict(points=[[1, 2, 3]]*101), dict(points=[[1, 2]]), dict(points=[[1, 2, True]]),
                        dict(points=[[1, 2, float('nan')]]), dict(points=[[1, 2, float('inf')]]),
                        dict(points=[[10**400, 0, 0]])]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                decode(packet(**changes))
        for raw in (b'{}', b'{broken', b'{\xff}', packet().replace(b'"v":', b'"v":1,"v":')):
            with self.assertRaises(ValueError):
                decode(raw)

    def test_fragmentation_boot_and_resync(self):
        r = LineReader()
        self.assertEqual(list(r.feed(b'booting\r\n'+packet()[:10])), [])
        self.assertEqual(list(r.feed(packet()[10:]+b'\r\n'))[0][0][0]['seq'], 1)
        self.assertIsNotNone(list(r.feed(b'x'*(MAX_LINE+1)))[0][1])
        events = list(r.feed(packet()+b'\n{broken\n'+packet()+b'\n'))
        self.assertEqual(len(events), 2)
        self.assertIsNotNone(events[0][1])
        self.assertEqual(events[1][0][1], packet())


class SessionTest(unittest.TestCase):
    def test_round_trip_host_timing(self):
        out = io.BytesIO()
        with patch('builtins.open', return_value=out):
            rec = Recorder('unused', 10)
            rec.append(packet(seq=9, t_ms=999), 10.25)
            rec.append(packet(seq=0, t_ms=0), 11)
        with patch('builtins.open', return_value=io.BytesIO(out.getvalue())):
            replay = Replay('unused', 2)
        self.assertFalse(replay.due(2.2))
        self.assertTrue(replay.due(2.25))
        self.assertEqual(replay.next['seq'], 9)
        replay.advance()
        self.assertFalse(replay.due(2.99))
        self.assertTrue(replay.due(3))
        replay.advance()
        self.assertIsNone(replay.next)
        replay.close()
        rec.close()

    def test_bad_session(self):
        for data in (b'bad', HEADER, HEADER+b'0\t{}\n', HEADER+b'x'*20000):
            with patch('builtins.open', return_value=io.BytesIO(data)), self.assertRaises(ValueError):
                Replay('unused', 1)
        data = HEADER + b'5\t'+packet()+b'\n2\t'+packet()+b'\n'
        with patch('builtins.open', return_value=io.BytesIO(data)):
            replay = Replay('unused', 1)
        with self.assertRaisesRegex(ValueError, 'line 3'):
            replay.advance()
        replay.close()


class WindowTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = Viewer(self.root)
        self.root.update()
        self.addCleanup(self.app.close)

    def button(self, label):
        for tab in self.app.nav.tabs():
            frame = self.root.nametowidget(tab)
            for child in frame.winfo_children():
                if 'text' in child.keys() and child.cget('text') == label:
                    self.app.nav.select(tab)
                    return child
        self.fail(f'button not found: {label}')

    def test_loop_serial_pause_record_clear_and_disconnect(self):
        port = serial.serial_for_url('loop://', timeout=0)
        self.addCleanup(port.close)
        self.app.port.set('TEST')
        with patch('radar_viewer.serial.Serial', return_value=port) as factory:
            self.button('Connect').invoke()
            factory.assert_called_once_with('TEST', 115200, timeout=0)
        self.app.recording = Mock()
        now = time.monotonic()
        port.write(b'boot\n'+packet()+b'\n')
        self.app.poll(now)
        self.assertEqual(len(self.app.plot.find_withtag('point')), 1)
        self.button('Pause display').invoke()
        port.write(packet(seq=2)+b'\n')
        self.app.poll(now+.1)
        self.assertEqual(self.app.shown['seq'], 1)
        self.assertEqual(self.app.frames, 2)
        self.assertEqual(self.app.recording.append.call_count, 2)
        self.button('Pause display').invoke()
        self.assertEqual(self.app.shown['seq'], 2)
        self.button('Pause display').invoke()
        self.app.poll(now+STALE_SECONDS+1)
        self.assertFalse(self.app.plot.find_withtag('point'))
        self.assertIn('STALE', self.app.status.get())
        self.button('Disconnect / Stop').invoke()
        self.assertFalse(port.is_open)
        self.assertIn('DISCONNECTED', self.app.status.get())

    def test_navigation_status_and_sensor_origin(self):
        app = self.app
        self.assertEqual(self.root.title(), 'mmWave Radar')
        self.assertEqual([app.nav.tab(t, 'text') for t in app.nav.tabs()],
                         ['Connection', 'Session', 'Demo', 'Display', 'Log'])
        self.assertEqual(app.badge.cget('text'), 'Disconnected')
        self.button('Synthetic demo').invoke()
        app.poll(time.monotonic())
        self.assertEqual(app.badge.cget('text'), 'Point cloud')
        self.assertEqual(app.metrics['Source'].get(), 'demo')
        self.button('Clear log').invoke()
        self.assertEqual(app.logbox.size(), 0)
        app.stop()
        for zoom in ('1', '8'):
            app.range.set(zoom)
            app.render()
            plot = app.plot
            x, y = plot.winfo_width()/2, plot.winfo_height()-48
            self.assertEqual(plot.coords('sensor-icon'), [x, y-10, x+8, y+6, x-8, y+6])
            self.assertFalse(plot.find_withtag('point'))

    def test_status_hover_help(self):
        help_ui = self.app.help
        for label in self.app.badge.master.winfo_children():
            self.assertIn(label, help_ui.texts)
        self.assertIn(self.app.baud, help_ui.texts)
        self.assertEqual(help_ui.delay_ms, 1200)
        help_ui.delay_ms = 10
        self.app.badge.event_generate('<Enter>')
        self.assertIsNone(help_ui.popup)
        deadline = time.monotonic() + 1
        while help_ui.popup is None and time.monotonic() < deadline:
            self.root.update()
        self.assertIsNotNone(help_ui.popup)
        self.app.badge.event_generate('<Leave>')
        self.assertIsNone(help_ui.popup)
        self.app.badge.event_generate('<Enter>')
        self.app.badge.event_generate('<ButtonPress-1>')
        self.assertIsNone(help_ui.timer)

    def test_front_view_clips_only_rendering(self):
        self.app.demo()
        raw = packet(points=[[-1, 2, 0], [1, 2, 0], [0, -1, 0], [0, 0, 0]])
        now = time.monotonic()
        self.app.accept(decode(raw), raw, now)
        self.app.render(now)
        self.assertEqual(len(self.app.plot.find_withtag('point')), 3)
        self.assertEqual(self.app.metrics['Points'].get(), '4')
        self.assertEqual(self.app.latest['points'][2], [0, -1, 0])
        button = self.button('Synthetic demo')
        self.assertEqual(self.app.nav.tab(button.master, 'text'), 'Demo')

    def test_read_budget_and_unplug(self):
        self.app.mode = 'LIVE'
        self.app.reader = LineReader()
        port = self.app.stream = Mock(in_waiting=999999)
        port.read.return_value = packet()+b'\n'
        self.app.poll(time.monotonic())
        port.read.assert_called_once_with(READ_BYTES)
        port.read.side_effect = serial.SerialException('emulated unplug')
        self.root.after_cancel(self.app.timer)
        self.app.tick()
        self.assertEqual(self.app.mode, 'DISCONNECTED')
        self.assertFalse(self.app.plot.find_withtag('point'))

    def test_demo_window_and_replay(self):
        self.button('Synthetic demo').invoke()
        deadline = time.monotonic()+1
        while not self.app.frames and time.monotonic() < deadline:
            self.root.update()
        self.assertIn('Source: demo', self.app.status.get())
        self.assertTrue(self.app.plot.find_withtag('point'))
        self.button('Disconnect / Stop').invoke()
        saved = HEADER+b'0\t'+packet()+b'\n500\t'+packet(seq=2, state='no_cloud', points=[])+b'\n'
        with patch('radar_viewer.filedialog.askopenfilename', return_value='saved.radar'), patch('builtins.open', return_value=io.BytesIO(saved)):
            self.button('Replay session…').invoke()
        start = self.app.stream.start
        self.app.poll(start+.1)
        self.assertIn('REPLAY', self.app.status.get())
        self.assertEqual(self.app.frames, 1)
        self.button('Pause display').invoke()
        self.app.poll(start+.51)
        self.assertFalse(self.app.plot.find_withtag('point'))
        self.assertIn('no_cloud', self.app.status.get())
        self.app.poll(start+.53)
        self.assertEqual(self.app.mode, 'DISCONNECTED')
