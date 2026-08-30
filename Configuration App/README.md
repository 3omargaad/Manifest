# Macropad Configuration App

A desktop GUI for configuring the 3×4 macropad (Raspberry Pi Pico / CircuitPython).  
Built with **PyQt6** — no system Tk dependency, works on macOS 13+.

## Quick start

```bash
# Install PyQt6 + pyserial into Python 3.9 (ships with Xcode tools, has no Tk issues)
/usr/bin/pip3 install PyQt6 pyserial

# Run
/usr/bin/python3 app.py
```

> If you use a venv:  `python -m pip install PyQt6 pyserial && python app.py`

## What it does

| Panel | Description |
|-------|-------------|
| **Top bar** | Choose the coding language. Connection status shows the Pico's serial port when plugged in. |
| **Key grid (left)** | 3 × 4 layout. First 8 keys are enabled (green). Click any key to edit it. |
| **Key config (right)** | Edit name, type (macro / keystroke / sequence / custom), value fields. Sequence and keystroke are mutually exclusive. Custom Value overrides both. |
| **Bottom bar** | **Export to Pico** — writes `config.json` to the `CIRCUITPY` drive. **Save locally** — saves next to `app.py`. **Save As…** — pick any path. |

## Key type reference

| Type | Field used | Example |
|------|-----------|---------|
| `macro` / `sequence` | Sequence | `for i in range():\n` |
| `keystroke` | Keystroke | `COMMAND+SHIFT+B` |
| `custom` | Custom Value | any raw string |

Valid keystroke tokens: `COMMAND`, `CTRL`, `ALT`, `SHIFT`, `ENTER`, `ESC`, `TAB`, `SPACE`, `BACKSPACE`, `DELETE`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `F1`–`F12`, `A`–`Z`, `0`–`9`, `GRAVE_ACCENT`.
