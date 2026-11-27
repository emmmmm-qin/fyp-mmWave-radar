"""Shared light palette for the viewer's instrument panels."""
from tkinter import ttk

BG = '#ffffff'
PANEL = '#f7f9fb'
GRID = '#dce3e9'
TEXT = '#263846'
MUTED = '#536976'
ACCENT = '#427b74'
POINT = '#557fa5'
RING = '#b3c9c9'
SELECTED = '#e2eeec'
FONT = ('Segoe UI', 10)


def apply(root):
    root.configure(background=BG)
    root.option_add('*Font', FONT)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=PANEL, foreground=TEXT, font=FONT,
                    bordercolor=GRID, lightcolor=PANEL, darkcolor=PANEL)
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', background=BG, padding=(14, 6), borderwidth=0)
    style.map('TNotebook.Tab', background=[('selected', SELECTED), ('active', PANEL)],
              foreground=[('selected', ACCENT)])
    style.configure('TButton', background=BG, padding=(9, 4), relief='flat')
    style.map('TButton', background=[('pressed', GRID), ('active', SELECTED)])
    style.map('TCheckbutton', background=[('active', SELECTED)])
    style.configure('TCombobox', fieldbackground=BG, foreground=TEXT, arrowcolor=MUTED)
    style.map('TCombobox', fieldbackground=[('readonly', BG)], foreground=[('readonly', TEXT)])
    style.configure('Caption.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 10, 'bold'))
