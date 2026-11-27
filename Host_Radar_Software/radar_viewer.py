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
        root.title('mmWave Radar')
        root.minsize(660, 500)
        self.mode = 'DISCONNECTED'
        self.stream = self.recording = self.latest = self.shown = None
        self.frames = 0
        self.last = self.start = 0
        self.paused = tk.BooleanVar()
        self.status = tk.StringVar()
        self.range = tk.StringVar(value='4')
        ttk.Label(root, text='mmWave Radar', padding=(12, 6),
                  font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        self.nav = ttk.Notebook(root)
        self.nav.pack(fill='x', padx=10)
        top, session, display, diagnostics = [ttk.Frame(self.nav, padding=6) for _ in range(4)]
        for tab, name in zip((top, session, display, diagnostics),
                             ('Connection', 'Session', 'Display', 'Log')):
            self.nav.add(tab, text=name)
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
        for label, cmd in [('Synthetic demo', self.demo), ('Replay session…', self.replay),
                           ('Record / Stop…', self.record), ('Stop session', self.stop)]:
            ttk.Button(session, text=label, command=cmd).pack(side='left', padx=2)
        ttk.Checkbutton(display, text='Pause display', variable=self.paused, command=self.render).pack(side='left')
        ttk.Label(display, text='Range ±m', padding=(12, 0)).pack(side='left')
        zoom = ttk.Combobox(display, textvariable=self.range, state='readonly', width=4, values=(1, 2, 4, 8, 16, 32))
        zoom.pack(side='left')
        zoom.bind('<<ComboboxSelected>>', lambda _: self.render())
        panel = tk.Frame(root, bg='#193449', padx=12, pady=8)
        panel.pack(fill='x', padx=10, pady=8)
        tk.Label(panel, text='RADAR STATUS', bg='#193449', fg='white',
                 font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky='w')
        self.badge = tk.Label(panel, padx=10, font=('Segoe UI', 10, 'bold'))
        self.badge.grid(row=0, column=1, columnspan=2, sticky='w')
        self.flags = tk.Label(panel, bg='#193449', fg='#ffda83')
        self.flags.grid(row=0, column=3, columnspan=2, sticky='e')
        self.metrics = {}
        for col, name in enumerate(('Mode', 'Source', 'Frames', 'Display seq', 'Points')):
            panel.columnconfigure(col, weight=1, uniform='metrics')
            tk.Label(panel, text=name, bg='#193449', fg='#abc4d3').grid(row=1, column=col, sticky='w', pady=(7, 0))
            value = tk.StringVar()
            tk.Label(panel, textvariable=value, bg='#193449', fg='white',
                     font=('Segoe UI', 10, 'bold')).grid(row=2, column=col, sticky='w')
            self.metrics[name] = value
        ttk.Label(root, text='Top-down viewer   ·   Sensor coordinates   /   +Y forward',
                  padding=(12, 2)).pack(anchor='w')
        self.plot = Plot(root)
        self.plot.pack(fill='both', expand=True)
        self.logbox = tk.Listbox(root, height=5)
        self.logbox.pack(fill='x')
        ttk.Button(diagnostics, text='Clear log', command=lambda: self.logbox.delete(0, 'end')).pack(side='left')
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
        summary = f'{self.mode}{flags} | {state} | Source: {source} | Frames: {self.frames} | Display seq: {seq} | Points: {len(points)}'
        if summary != self.status.get():
            self.status.set(summary)
            text, color = {
                'idle': ('Disconnected', '#e2e8ef'), 'waiting': ('Waiting for a frame', '#ffe2a3'),
                'STALE': ('Stale data', '#ffc9b9'), 'unavailable': ('Radar data unavailable', '#ffc9b9'),
                'no_cloud': ('Frame without cloud', '#d6e6ef'), 'cloud': ('Point cloud', '#afe8da'),
            }[state]
            self.badge.configure(text=text, background=color, foreground='#152d3b')
            self.flags.configure(text=flags.replace(' | ', '  ').strip())
            for name, value in zip(self.metrics, (self.mode, source, self.frames, seq, len(points))):
                self.metrics[name].set(value)

    def close(self):
        self.root.after_cancel(self.timer)
        self.stop()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    Viewer(root)
    root.mainloop()
