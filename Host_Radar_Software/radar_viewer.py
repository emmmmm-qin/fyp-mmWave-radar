"""Windows host viewer. Nothing opens a serial port until Connect is pressed."""
import json
import math
import time
import tkinter as tk
from tkinter import filedialog, ttk

import serial
from serial.tools import list_ports

from plot import Plot
from protocol import LineReader
from session import Recorder, Replay

READ_BYTES = 8192
STALE_SECONDS = 1.5


class Viewer:
    def __init__(self, root):
        self.root = root
        root.title('FYP radar · top-down viewer')
        self.mode = 'DISCONNECTED'
        self.stream = self.recording = self.latest = self.shown = None
        self.frames = 0
        self.last = self.start = 0
        self.paused = tk.BooleanVar()
        self.status = tk.StringVar()
        self.range = tk.StringVar(value='4')
        top = ttk.Frame(root, padding=5)
        top.pack(fill='x')
        ttk.Label(top, text='Port').pack(side='left')
        self.port = ttk.Combobox(top, width=13)
        self.port.pack(side='left')
        ttk.Button(top, text='Refresh', command=self.refresh).pack(side='left')
        ttk.Label(top, text='Baud').pack(side='left')
        self.baud = ttk.Combobox(top, width=9, values=(115200, 460800, 921600))
        self.baud.set('115200')
        self.baud.pack(side='left')
        for label, cmd in [('Connect', self.connect), ('Disconnect / Stop', self.stop)]:
            ttk.Button(top, text=label, command=cmd).pack(side='left')
        tools = ttk.Frame(root, padding=5)
        tools.pack(fill='x')
        for label, cmd in [('Synthetic demo', self.demo), ('Replay session…', self.replay), ('Record / Stop…', self.record)]:
            ttk.Button(tools, text=label, command=cmd).pack(side='left')
        ttk.Checkbutton(tools, text='Pause display', variable=self.paused, command=self.render).pack(side='left')
        ttk.Label(tools, text='Range ±m').pack(side='left')
        zoom = ttk.Combobox(tools, textvariable=self.range, state='readonly', width=4, values=(1, 2, 4, 8, 16, 32))
        zoom.pack(side='left')
        zoom.bind('<<ComboboxSelected>>', lambda _: self.render())
        ttk.Label(root, textvariable=self.status, padding=5).pack(fill='x')
        self.plot = Plot(root)
        self.plot.pack(fill='both', expand=True)
        self.logbox = tk.Listbox(root, height=5)
        self.logbox.pack(fill='x')
        ttk.Button(root, text='Clear log', command=lambda: self.logbox.delete(0, 'end')).pack(anchor='e')
        self.log('Select Refresh to list ports, or start Synthetic demo without hardware.')
        self.render()
        self.timer = root.after(20, self.tick)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def log(self, text):
        self.logbox.insert('end', f'{time.strftime("%H:%M:%S")}  {text}')
        if self.logbox.size() > 150:
            self.logbox.delete(0)
        self.logbox.see('end')

    def refresh(self):
        try:
            ports = [p.device for p in list_ports.comports()]
            self.port['values'] = ports
            if self.port.get() not in ports:
                self.port.set(ports[0] if ports else '')
            self.log(f'Found {len(ports)} serial port(s).')
        except OSError as exc:
            self.log(f'Port refresh failed: {exc}')

    def connect(self):
        if self.mode != 'DISCONNECTED':
            self.log('Stop the current input before connecting.')
            return
        try:
            if not self.port.get().strip():
                raise ValueError('select or enter a COM port')
            self.stream = serial.Serial(self.port.get().strip(), int(self.baud.get()), timeout=0)
        except (ValueError, OSError, OverflowError) as exc:
            self.log(f'Connect failed: {exc}')
            return
        self.reader = LineReader()
        self.begin('LIVE')

    def begin(self, mode):
        self.mode = mode
        self.start = self.last = time.monotonic()
        self.frames = 0
        self.paused.set(False)
        self.log(f'Started {mode}.')
        self.render()

    def demo(self):
        if self.mode != 'DISCONNECTED':
            self.log('Stop the current input before starting the demo.')
            return
        self.begin('SYNTHETIC DEMO')

    def replay(self):
        if self.mode != 'DISCONNECTED':
            self.log('Stop the current input before replay.')
            return
        path = filedialog.askopenfilename(title='Open radar session', filetypes=[('Radar session', '*.radar'), ('All files', '*')])
        if path:
            try:
                self.stream = Replay(path, time.monotonic())
                self.begin('REPLAY')
            except (OSError, ValueError) as exc:
                self.log(f'Replay failed: {exc}')

    def record(self):
        if self.recording:
            self.end_record()
        elif self.mode not in ('LIVE', 'SYNTHETIC DEMO'):
            self.log('Recording requires live input or an explicit synthetic demo.')
        else:
            path = filedialog.asksaveasfilename(title='Save radar session', defaultextension='.radar', filetypes=[('Radar session', '*.radar')])
            if path:
                try:
                    self.recording = Recorder(path, time.monotonic())
                    self.log(f'Recording to {path}')
                except OSError as exc:
                    self.log(f'Record failed: {exc}')
        self.render()

    def end_record(self):
        if self.recording:
            try:
                self.recording.close()
                self.log('Recording stopped.')
            except OSError as exc:
                self.log(f'Recording close failed: {exc}')
            self.recording = None

    def stop(self):
        self.end_record()
        if self.stream:
            try:
                self.stream.close()
            except OSError as exc:
                self.log(f'Close failed: {exc}')
        self.stream = self.latest = self.shown = None
        self.mode = 'DISCONNECTED'
        self.frames = 0
        self.paused.set(False)
        self.render()
        self.log('Disconnected; display cleared.')

    def accept(self, packet, raw, now):
        self.frames += 1
        self.latest, self.last = packet, now
        if packet['state'] != 'cloud' or not packet['points']:
            self.shown = None  # Never leave old detections visible after an empty frame.
        if self.recording:
            try:
                self.recording.append(raw, now)
            except OSError as exc:
                self.log(f'Record write failed: {exc}')
                self.end_record()

    def poll(self, now):
        if self.mode == 'LIVE':
            size = min(self.stream.in_waiting, READ_BYTES)
            if size:
                errors = []
                for result, error in self.reader.feed(self.stream.read(size)):
                    if error:
                        errors.append(error)
                    else:
                        self.accept(*result, now)
                if errors:
                    self.log(f'Rejected {len(errors)} line(s): {errors[0]}')
        elif self.mode == 'SYNTHETIC DEMO' and (not self.frames or now-self.last >= 0.1):
            t = now - self.start
            packet = dict(protocol='fyp-radar', v=1, source='demo', seq=self.frames & 0xffffffff,
                          t_ms=int(t*1000), state='cloud', points=[[2*math.sin(t), 2+math.cos(t), -math.sin(t)]])
            self.accept(packet, json.dumps(packet).encode('ascii'), now)
        elif self.mode == 'REPLAY':
            if self.stream.next is None:
                self.log('End of replay.')
                self.stop()
                return
            for _ in range(32):
                if not self.stream.due(now):
                    break
                self.accept(self.stream.next, None, now)
                self.stream.advance()
        self.render(now)

    def tick(self):
        try:
            self.poll(time.monotonic())
        except (OSError, ValueError) as exc:
            self.log(f'{self.mode} input failed: {exc}')
            self.stop()
        self.timer = self.root.after(20, self.tick)

    def render(self, now=None):
        now = time.monotonic() if now is None else now
        stale = self.mode != 'DISCONNECTED' and now-self.last >= STALE_SECONDS
        if stale:
            self.shown = self.latest = None
        elif not self.paused.get() or (self.latest and not self.latest['points']):
            self.shown = self.latest
        p = self.shown
        points = p['points'] if p else []
        radius = int(self.range.get())
        if points != self.plot.points or radius != self.plot.radius:
            self.plot.points, self.plot.radius = points, radius
            self.plot.draw()
        state = p['state'] if p else ('STALE' if stale else ('waiting' if self.mode != 'DISCONNECTED' else 'idle'))
        source = p['source'] if p else '—'
        seq = p['seq'] if p else '—'
        flags = (' | PAUSED' if self.paused.get() else '') + (' | RECORDING' if self.recording else '')
        self.status.set(f'{self.mode}{flags} | {state} | Source: {source} | Frames: {self.frames} | Display seq: {seq} | Points: {len(points)}')

    def close(self):
        self.root.after_cancel(self.timer)
        self.stop()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    Viewer(root)
    root.mainloop()
