"""Equal-scale XY plot. Positive Y points up; the radar is at the origin."""
import tkinter as tk


class Plot(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, background='#fcfcfb', highlightthickness=0, height=360)
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
        if min(w, h) < 80:
            return
        cx, cy = w / 2, h / 2
        side = min(cx - 48, cy - 32)
        scale = side / self.radius
        for i in range(-2, 3):
            n = self.radius * i / 2
            x, y = cx + scale * n, cy - scale * n
            color = '#8d9298' if i == 0 else '#d9dcdf'
            self.create_line(x, cy-side, x, cy+side, fill=color)
            self.create_line(cx-side, y, cx+side, y, fill=color)
            self.create_text(x, cy+side+12, text=f'{n:g}')
            self.create_text(cx-side-8, y, text=f'{n:g}', anchor='e')
        self.create_text(cx, cy+side+25, text='X (m)')
        self.create_text(cx, cy-side-15, text='Y (m) · forward')
        for x, y, v in self.points:
            if abs(x) <= self.radius and abs(y) <= self.radius:
                px, py = cx + scale*x, cy - scale*y
                mark = self.create_oval(px-5, py-5, px+5, py+5, fill='#4677ba', outline='#fcfcfb', width=2, tags='point')
                self.labels[mark] = f'X {x:.2f} m   Y {y:.2f} m   v {v:.2f} m/s'

    def hover(self, event):
        self.delete('tooltip')
        for item in reversed(self.find_overlapping(event.x-4, event.y-4, event.x+4, event.y+4)):
            if item in self.labels:
                self.create_text(8, 8, anchor='nw', text=self.labels[item], tags='tooltip')
                break
