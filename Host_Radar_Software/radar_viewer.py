"""Windows host viewer. Nothing opens a serial port until Connect is pressed."""
import json
import math
import time
import tkinter as tk
from tkinter import filedialog, ttk

import serial
from serial.tools import list_ports

import theme
from hover_help import HoverHelp
from plot import Plot
from protocol import LineReader
from session import Recorder, Replay
from serial_monitor import SerialMonitor

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
        theme.apply(root)
        self.help = HoverHelp(root)
        self.nav = ttk.Notebook(root)
        self.nav.pack(fill='x', padx=10, pady=(8, 0))
        top, session, demo, display, diagnostics = [ttk.Frame(self.nav, padding=6) for _ in range(5)]
        for tab, name in zip((top, session, demo, display, diagnostics),
                             ('Connection', 'Session', 'Demo', 'Display', 'Log')):
            self.nav.add(tab, text=name)
        self.monitor_tab = ttk.Frame(self.nav, padding=6)
        self.nav.add(self.monitor_tab, text='Serial Monitor')
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
        ttk.Button(demo, text='Synthetic demo', command=self.demo).pack(side='left', padx=2)
        ttk.Button(demo, text='Stop demo', command=lambda: self.stop() if self.mode == 'SYNTHETIC DEMO' else None).pack(side='left')
        ttk.Label(demo, text='Simulated points · No device required', padding=(12, 0)).pack(side='left')
        for label, cmd in [('Replay session…', self.replay),
                           ('Record / Stop…', self.record), ('Stop session', self.stop)]:
            ttk.Button(session, text=label, command=cmd).pack(side='left', padx=2)
        ttk.Checkbutton(display, text='Pause display', variable=self.paused, command=self.render).pack(side='left')
        ttk.Label(display, text='Forward range (m)', padding=(12, 0)).pack(side='left')
        zoom = ttk.Combobox(display, textvariable=self.range, state='readonly', width=4, values=(1, 2, 4, 8, 16, 32))
        zoom.pack(side='left')
        zoom.bind('<<ComboboxSelected>>', lambda _: self.render())
        panel = tk.Frame(root, bg=theme.PANEL, padx=12, pady=8)
        panel.pack(fill='x', padx=10, pady=8)
        heading = tk.Label(panel, text='Radar status', bg=theme.PANEL, fg=theme.TEXT,
                           font=('Segoe UI', 12, 'bold'))
        heading.grid(row=0, column=0, sticky='w')
        self.help.register(heading, 'Connection and display information. A working USB link does not guarantee fresh radar data.')
        self.badge = tk.Label(panel, padx=10, font=('Segoe UI', 10, 'bold'))
        self.badge.grid(row=0, column=1, columnspan=2, sticky='w')
        self.help.register(self.badge, 'State of the displayed data. Stale means no recent valid packet; unavailable means the device reports no usable frame. Neither means the room is empty.')
        self.flags = tk.Label(panel, bg=theme.PANEL, fg=theme.ACCENT)
        self.help.register(self.flags, 'Paused freezes the view only. Recording saves accepted packets, even while the display is paused.')
        self.flags.grid(row=0, column=3, columnspan=2, sticky='e')
        self.metrics = {}
        metric_help = {
            'Mode': 'Where the viewer is reading from: a live COM port, a recorded session, or the synthetic demo.',
            'Source': 'Origin declared by the displayed packet: radar or demo. Replaying a recording preserves its original source.',
            'Frames': 'Total accepted packets in this session, including status messages. This keeps counting while the picture is paused.',
            'Display seq': 'Sequence number in the displayed packet, not the number of received frames. An unavailable heartbeat uses zero.',
            'Points': 'Number of detections in the displayed packet, including points outside the chart. This is not a count of people.',
        }
        for col, (name, explanation) in enumerate(metric_help.items()):
            panel.columnconfigure(col, weight=1, uniform='metrics')
            caption = tk.Label(panel, text=name, anchor='w', bg=theme.PANEL, fg=theme.MUTED)
            caption.grid(row=1, column=col, sticky='ew', pady=(8, 0))
            value = tk.StringVar()
            number = tk.Label(panel, textvariable=value, anchor='w', bg=theme.PANEL, fg=theme.TEXT,
                              font=('Segoe UI', 11, 'bold'))
            number.grid(row=2, column=col, sticky='ew')
            self.help.register(caption, explanation)
            self.help.register(number, explanation)
            self.metrics[name] = value
        self.body = ttk.Frame(root)
        self.body.pack(fill='both', expand=True, padx=10, pady=(0, 6))
        self.monitor = SerialMonitor(self.monitor_tab, self.body, self.help)
        self.chart = ttk.Frame(self.body)
        self.chart.pack(fill='both', expand=True)
        self.nav.bind('<<NotebookTabChanged>>', self.change_view)
        ttk.Label(self.chart, text='Top-down viewer   ·   Sensor coordinates   /   +Y forward',
                  style='Caption.TLabel', padding=(12, 2)).pack(anchor='w')
        self.plot = Plot(self.chart)
        self.plot.pack(fill='both', expand=True)
        ttk.Label(root, text='Event log', style='Caption.TLabel', padding=(12, 2)).pack(anchor='w')
        self.logbox = tk.Listbox(root, height=4, bg=theme.PANEL, fg=theme.MUTED, relief='flat',
                                 highlightthickness=0, selectbackground=theme.GRID, selectforeground=theme.TEXT)
        self.logbox.pack(fill='x', padx=10, pady=(0, 8))
        ttk.Button(diagnostics, text='Clear log', command=lambda: self.logbox.delete(0, 'end')).pack(side='left')
        controls = {
            'Port': 'Choose the Windows COM port of the ESP32 native USB connector.',
            'Baud': 'Host serial setting, normally 115200. This does not change the TI radar UART speed.',
            'Refresh': 'Find available COM ports without opening them.',
            'Connect': 'Start reading from the selected COM port. Close other serial monitors first.',
            'Disconnect / Stop': 'Stop the active input, close any recording and clear the displayed points.',
            'Synthetic demo': 'Generate example points on this PC; no device or serial connection is used.',
            'Stop demo': 'Stop the synthetic input without affecting a live connection or replay.',
            'Replay session…': 'Open a saved .radar file and replay it using its recorded arrival times.',
            'Record / Stop…': 'Start or stop saving accepted packets from live input or the demo.',
            'Stop session': 'End the active input session and close the recording if one is open.',
            'Pause display': 'Freeze the picture without stopping reception or recording. Stale detections still clear.',
            'Forward range (m)': 'Set the visible forward distance in metres. Left and right span the same distance; zoom never changes recorded points.',
            'Clear log': 'Clear the event messages on screen. Saved session files are not changed.',
        }
        for tab in (top, session, demo, display, diagnostics):
            for widget in tab.winfo_children():
                if 'text' in widget.keys() and widget.cget('text') in controls:
                    self.help.register(widget, controls[widget.cget('text')])
        for widget, key in ((self.port, 'Port'), (self.baud, 'Baud'), (zoom, 'Forward range (m)')):
            self.help.register(widget, controls[key])
        self.log('Select Refresh to list ports, or start Synthetic demo without hardware.')
        self.render()
        self.timer = root.after(20, self.tick)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def change_view(self, _event=None):
        if self.nav.select() == str(self.monitor_tab):
            self.chart.pack_forget()
            self.monitor.panel.pack(fill='both', expand=True)
            self.monitor.resume()
        else:
            self.monitor.panel.pack_forget()
            self.chart.pack(fill='both', expand=True)

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
        self.monitor.set_source(mode, self.port.get().strip() if mode == 'LIVE' else None)
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
        self.monitor.set_source(self.mode)
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
                data = self.stream.read(size)
                self.monitor.feed(data)
                for result, error in self.reader.feed(data):
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
        if self.nav.select() == str(self.monitor_tab):
            self.monitor.render(now)
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
                'idle': ('Disconnected', '#e9edf1'), 'waiting': ('Waiting for a frame', '#f6efde'),
                'STALE': ('Stale data', '#f6e9e4'), 'unavailable': ('Radar data unavailable', '#f6e9e4'),
                'no_cloud': ('Frame without cloud', '#e7eef4'), 'cloud': ('Point cloud', theme.SELECTED),
            }[state]
            self.badge.configure(text=text, background=color, foreground='#152d3b')
            self.flags.configure(text=flags.replace(' | ', '  ').strip())
            for name, value in zip(self.metrics, (self.mode, source, self.frames, seq, len(points))):
                self.metrics[name].set(value)

    def close(self):
        self.help.hide()
        self.root.after_cancel(self.timer)
        self.stop()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    Viewer(root)
    root.mainloop()
