"""Front-facing, equal-scale XY view. Only the drawing clips rearward points."""
import tkinter as tk

import theme


class Plot(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, background=theme.BG, highlightthickness=1,
                         highlightbackground=theme.GRID, height=340)
        self.radius = 4
        self.points = []
        self.labels = {}
        self.bind('<Configure>', lambda _: self.draw())
        self.bind('<Motion>', self.hover)
        self.bind('<Leave>', lambda _: self.delete('tooltip'))

    def draw(self):
        self.delete('all')
        self.labels.clear()
        w, h = self.winfo_width(), self.winfo_height()
        cx, cy = w / 2, h - 48
        side = min(cx - 52, cy - 26)
        if side < 32:
            return
        scale = side / self.radius
        left, right, top = cx-side, cx+side, cy-side
        self.create_rectangle(left, top, right, cy, fill=theme.PANEL, outline=theme.GRID)
        for i in range(-4, 5):
            x = cx + side*i/4
            self.create_line(x, top, x, cy, fill=theme.GRID)
            if i and i % 2 == 0:
                self.create_text(x, cy+14, text=f'{self.radius*i/4:g}', fill=theme.MUTED)
        for i in range(5):
            y = cy - side*i/4
            self.create_line(left, y, right, y, fill=theme.GRID)
            self.create_text(left-8, y, text=f'{self.radius*i/4:g}', anchor='e', fill=theme.MUTED)
            if i:
                # Range guides are distances from the sensor, not a field-of-view limit.
                r = side*i/4
                self.create_arc(cx-r, cy-r, cx+r, cy+r, start=0, extent=180,
                                style='arc', outline=theme.RING, dash=(3, 5))
        self.create_line(cx, cy, cx, top, arrow='last', fill=theme.ACCENT)
        self.create_text(cx, top-12, text='+Y  ·  Forward (m)', fill=theme.MUTED)
        self.create_text(right, cy+33, text='X (m)', anchor='e', fill=theme.MUTED)
        self.create_polygon(cx, cy-10, cx+8, cy+6, cx-8, cy+6,
                            fill=theme.ACCENT, outline=theme.BG, tags=('sensor', 'sensor-icon'))
        self.create_text(cx, cy+24, text='Radar  (0, 0)', fill=theme.ACCENT, tags='sensor')
        for x, y, v in self.points:
            if abs(x) <= self.radius and 0 <= y <= self.radius:
                px, py = cx + scale*x, cy - scale*y
                mark = self.create_oval(px-5, py-5, px+5, py+5, fill=theme.POINT,
                                        outline=theme.BG, width=2, tags='point')
                self.labels[mark] = f'X {x:.2f} m   Y {y:.2f} m   v {v:.2f} m/s'

    def hover(self, event):
        self.delete('tooltip')
        for item in reversed(self.find_overlapping(event.x-4, event.y-4, event.x+4, event.y+4)):
            if item in self.labels:
                self.create_text(8, 5, anchor='nw', text=self.labels[item], fill=theme.TEXT, tags='tooltip')
                break
