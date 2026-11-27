"""A bounded, read-only view of bytes already received by the live viewer."""
import tkinter as tk
from tkinter import ttk

import theme

HISTORY_BYTES = 8192
REFRESH_SECONDS = 0.1
# LF lays out the original lines. Escape backslash too, so literal escape-looking
# device text remains distinguishable from a control or non-ASCII byte.
_GLYPHS = tuple('\n' if b == 10 else '\\\\' if b == 92 else chr(b) if 32 <= b < 127
                else f'\\x{b:02x}' for b in range(256))


def escaped(data):
    return ''.join(map(_GLYPHS.__getitem__, data))


class SerialMonitor:
    def __init__(self, controls, parent, help_ui):
        self.buffer = bytearray()
        self.total = 0
        self.drawn = b''
        self.drawn_end = 0
        self.next_refresh = 0
        self.source = 'Disconnected · No serial input'
        self.port = None
        self.frozen = tk.BooleanVar(master=parent)
        label = self.label = ttk.Label(controls, text=self.source)
        label.pack(side='left', padx=(0, 8))
        freeze = ttk.Checkbutton(controls, text='Freeze monitor', variable=self.frozen,
                                 command=self.resume)
        freeze.pack(side='left')
        clear = ttk.Button(controls, text='Clear', command=self.clear)
        clear.pack(side='left', padx=4)
        help_ui.register(label, 'Actual receive port. Demo and replay do not produce serial traffic.')
        help_ui.register(freeze, 'Hold this text for selection or copying. Live capture, plotting and recording continue.')
        help_ui.register(clear, 'Discard monitor history only; this does not flush the port or reset the packet parser.')
        self.panel = ttk.Frame(parent)
        self.panel.columnconfigure(0, weight=1)
        self.panel.rowconfigure(0, weight=1)
        self.text = tk.Text(self.panel, wrap='none', width=1, height=4, state='disabled',
                            font='TkFixedFont', bg=theme.PANEL, fg=theme.TEXT, relief='flat',
                            selectbackground=theme.GRID, selectforeground=theme.TEXT,
                            highlightbackground=theme.GRID, highlightcolor=theme.ACCENT)
        self.text.grid(row=0, column=0, sticky='nsew')
        for axis, row, col, sticky, orient in [('y', 0, 1, 'ns', 'vertical'), ('x', 1, 0, 'ew', 'horizontal')]:
            bar = ttk.Scrollbar(self.panel, orient=orient, command=getattr(self.text, axis + 'view'))
            bar.grid(row=row, column=col, sticky=sticky)
            self.text.configure(**{axis + 'scrollcommand': bar.set})

    def set_source(self, mode, port=None):
        if mode != 'DISCONNECTED':
            self.port = port
            self.frozen.set(False)
            self.clear()
        if mode == 'LIVE':
            self.source = f'Live RX · {port}'
        elif mode == 'DISCONNECTED' and self.port:
            self.source = f'Disconnected · Last RX: {self.port}'
        else:
            self.source = f'{mode.title()} · No serial input'
        self.update_label()

    def update_label(self):
        dropped = self.total - len(self.buffer)
        self.label.configure(text=self.source + (f' · {dropped:,} older bytes discarded' if dropped else ''))

    def clear(self):
        self.buffer.clear()
        self.total = self.drawn_end = 0
        self.drawn = b''
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.configure(state='disabled')
        self.update_label()
        self.next_refresh = 0

    def feed(self, data):
        self.total += len(data)
        self.buffer.extend(data[-HISTORY_BYTES:])
        del self.buffer[:max(0, len(self.buffer) - HISTORY_BYTES)]

    def resume(self):
        self.next_refresh = 0
        self.render(0)

    def render(self, now):
        if self.frozen.get() or self.drawn_end == self.total or now < self.next_refresh:
            return
        self.next_refresh = now + REFRESH_SECONDS
        start = self.total - len(self.buffer)
        removed = min(len(self.drawn), start - (self.drawn_end - len(self.drawn)))
        follow = self.text.yview()[1] >= 0.999
        self.text.configure(state='normal')
        if removed:
            chars = len(escaped(self.drawn[:removed]))
            self.text.delete('1.0', f'1.0 + {chars} chars')
        self.text.insert('end', escaped(self.buffer[max(0, self.drawn_end - start):]))
        self.text.configure(state='disabled')
        if follow:
            self.text.yview_moveto(1)
        self.drawn, self.drawn_end = bytes(self.buffer), self.total
        self.update_label()
