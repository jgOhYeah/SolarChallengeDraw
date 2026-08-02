"""solarcardrawtheme_theme.py
Styling for the GUI in the solar challenge draw.
Written by Jotham Gates, created using ttkbootstrap ttkcreator, 28/06/2026"""
from ttkbootstrap.style import ThemeDefinition

theme = ThemeDefinition(
    name="solarcardrawtheme",
    themetype="light",
    colors={
        "primary": "#00804b",
        "secondary": "#adb5bd",
        "success": "#02b875",
        "info": "#17a2b8",
        "warning": "#f0ad4e",
        "danger": "#d9534f",
        "light": "#F8F9FA",
        "dark": "#343A40",
        "bg": "#ffffff",
        "fg": "#343a40",
        "selectbg": "#adb5bd",
        "selectfg": "#ffffff",
        "border": "#bfbfbf",
        "inputfg": "#343a40",
        "inputbg": "#fff",
        "active": "#e5e5e5",
    },
)