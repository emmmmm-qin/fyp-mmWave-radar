"""One non-modal tooltip shared by all registered controls."""
import tkinter as tk

import theme


class HoverHelp:
    def __init__(self, root, delay_ms=1200):
        self.root = root
        self.delay_ms = delay_ms
        self.timer = self.popup = None
        self.texts = {}
        root.bind('<Escape>', self.hide, add='+')

    def register(self, widget, text):
        self.texts[widget] = text
        widget.bind('<Enter>', lambda e: self.schedule(widget), add='+')
        for event in ('<Leave>', '<ButtonPress>', '<Unmap>', '<Destroy>'):
            widget.bind(event, self.hide, add='+')

    def schedule(self, widget):
        self.hide()
        self.timer = self.root.after(self.delay_ms, lambda: self.show(widget))

    def show(self, widget):
        self.timer = None
        if not widget.winfo_exists() or not widget.winfo_ismapped():
            return
        tip = self.popup = tk.Toplevel(self.root)
        tip.withdraw()
        tip.overrideredirect(True)
        tip.transient(self.root)
        tk.Label(tip, text=self.texts[widget], wraplength=320, justify='left',
                 bg=theme.BG, fg=theme.TEXT, padx=10, pady=7, highlightthickness=1,
                 highlightbackground='#aebfc7').pack()
        tip.update_idletasks()
        x, y = widget.winfo_pointerxy()
        width, height = tip.winfo_reqwidth(), tip.winfo_reqheight()
        # Prefer below the pointer; flip above it near the bottom of the display.
        x = max(0, min(x + 12, widget.winfo_screenwidth() - width))
        y = y + 20 if y + 20 + height <= widget.winfo_screenheight() else max(0, y - height - 8)
        tip.geometry(f'+{x}+{y}')
        tip.deiconify()

    def hide(self, _event=None):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.popup is not None:
            self.popup.destroy()
            self.popup = None
