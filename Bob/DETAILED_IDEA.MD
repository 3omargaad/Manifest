# Manifest — Programmable Developer Macropad
## Detailed Idea Document

**Platform:** Raspberry Pi Pico (RP2040)  
**Language:** MicroPython  
**Power:** USB (5V, bus-powered — no battery required)  
**License:** Open Source (MIT)  
**Target OS:** macOS

---

## 1. Hardware Overview

### MCU — Raspberry Pi Pico (RP2040)
- Dual-core ARM Cortex-M0+ at 133 MHz
- 264 KB SRAM, 2 MB onboard flash (stores firmware + keybind config JSON)
- Native USB support (USB 1.1 Full Speed) — used for USB HID emulation
- 26 usable GPIO pins — sufficient for a 3×4 matrix
- Low cost (~$4 USD), widely available, excellent MicroPython support

### Button Matrix — 3×4 (12 keys)
A keyboard matrix reduces GPIO usage from 12 individual pins down to 7 (3 rows + 4 columns).

**Wiring:**
- 3 row pins: GPIO 2, 3, 4
- 4 column pins: GPIO 6, 7, 8, 9
- Each key sits at a row/column intersection
- Row pins use internal pull-down resistors
- Each column pin is driven HIGH one at a time during scanning (column-strobe method)
- A diode (1N4148) per key prevents "ghosting" when multiple keys are pressed simultaneously

**Switches — Outemu Red (Linear)**
- Linear switches: smooth keypress with no tactile bump or click
- Actuation force ~45 gf, 4mm travel, 2mm actuation point
- Quiet and fast — good for rapid repeated macro triggers
- Hand-wired directly to the Pico GPIO pins via diodes

### Additional Components
- 1× USB-C or Micro-USB cable (matching the Pico variant in use)
- Hand-wired perfboard or bare wire soldering — no PCB required
- 3D-printed or laser-cut case/plate to hold switches in a 3×4 grid

---

## 2. Key Layout — 3×4 Grid (12 keys)

```
+--------+--------+--------+--------+
|  K01   |  K02   |  K03   |  K04   |
|  Run   | Build  |  Git   |  Git   |
|  Prog  | /Comp  | Commit | Push   |
+--------+--------+--------+--------+
|  K05   |  K06   |  K07   |  K08   |
|  Open  |  New   |  Open  |  Save  |
| Server |  File  |  Term  |  All   |
+--------+--------+--------+--------+
|  K09   |  K10   |  K11   |  ◈ K12 |
|  Copy  | Paste  | Format |  STT   |
|        |        |  Code  | (Siri) |
+--------+--------+--------+--------+
```

> **K12 (bottom-right)** is the AI / Speech-to-Text key. It has a unique **◈** symbol engraved or printed on its keycap to distinguish it visually at a glance — standard 1U size, same as all other keys.

---

## 3. Default Keybind Actions

All macOS shortcuts. Keybinds are stored in `/config.json` on the Pico's flash and are fully remappable via the companion UI.

| Key | Label | Default Action (macOS) | Notes |
|-----|-------|------------------------|-------|
| K01 | Run Program | `F5` | VS Code run / debug |
| K02 | Build / Compile | `Cmd+Shift+B` | VS Code build task |
| K03 | Git Commit | Macro: `git commit -m ""` + cursor in quotes | Types in active terminal |
| K04 | Git Push | Macro: `git push` + Return | Types in active terminal |
| K05 | Open Local Server | Macro: `python3 -m http.server` + Return | Configurable per project |
| K06 | New File | `Cmd+N` | Creates new untitled file |
| K07 | Open Terminal | `` Ctrl+` `` | VS Code integrated terminal toggle |
| K08 | Save All | `Cmd+Option+S` | Saves all open editors |
| K09 | Copy | `Cmd+C` | Standard clipboard copy |
| K10 | Paste | `Cmd+V` | Standard clipboard paste |
| K11 | Format Code | `Shift+Option+F` | VS Code format document |
| ◈ K12 | STT / AI | macOS Dictation (`Fn Fn`) | Activates macOS native Dictation — no extra software needed |

---

## 4. Firmware Design (MicroPython)

### 4.1 USB HID Emulation
The Pico presents itself to the host as a **USB HID Keyboard** device using the `adafruit_hid` library (CircuitPython-compatible, used via MicroPython shim) or the built-in `usb_hid` module.

```
USB Descriptor:
  - Device Class: HID
  - Interface: Keyboard (Boot Protocol)
```

For macro sequences (e.g. typing a git command string), the firmware sends individual `Keycode` presses with ~15 ms delays between characters.

### 4.2 Matrix Scanning Loop

```
Main loop (runs every ~5 ms):
  for each column c in [0..3]:
    drive column c HIGH
    for each row r in [0..2]:
      read GPIO row r
      if HIGH → key (r, c) is pressed
    drive column c LOW
  → debounce → compare with previous state → fire action on state change
```

**Debounce:** Time-based — key state must be stable for 20 ms before registering. Outemu Reds are linear so bounce is minimal, but debounce is kept for safety.

### 4.3 Config Storage

Keybinds are stored as `/config.json` on the Pico's filesystem:

```json
{
  "keys": {
    "K01": { "label": "Run",       "type": "hid",   "keys": ["F5"] },
    "K02": { "label": "Build",     "type": "hid",   "keys": ["CMD", "SHIFT", "B"] },
    "K03": { "label": "Git Commit","type": "macro",  "sequence": "git commit -m \"\"" },
    "K04": { "label": "Git Push",  "type": "macro",  "sequence": "git push\n" },
    "K05": { "label": "Server",    "type": "macro",  "sequence": "python3 -m http.server\n" },
    "K06": { "label": "New File",  "type": "hid",   "keys": ["CMD", "N"] },
    "K07": { "label": "Terminal",  "type": "hid",   "keys": ["CTRL", "GRAVE"] },
    "K08": { "label": "Save All",  "type": "hid",   "keys": ["CMD", "OPTION", "S"] },
    "K09": { "label": "Copy",      "type": "hid",   "keys": ["CMD", "C"] },
    "K10": { "label": "Paste",     "type": "hid",   "keys": ["CMD", "V"] },
    "K11": { "label": "Format",    "type": "hid",   "keys": ["SHIFT", "OPTION", "F"] },
    "K12": { "label": "STT",       "type": "hid",   "keys": ["FN", "FN"] }
  }
}
```

Supported action types:
- `"hid"` — single keypress or chord
- `"macro"` — types a string character by character into the active window

### 4.4 Speech-to-Text (◈ K12) Flow
K12 sends a double-tap of the macOS `Fn` key, which activates **macOS native Dictation** — the built-in system microphone activates and transcribes speech directly into whatever input field or editor is focused. No extra software, daemon, or API key is required.

---

## 5. Companion Configuration UI

### Purpose
On USB connection, a lightweight companion app lets developers remap any key without editing JSON manually or reflashing firmware.

### Tech Stack
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Backend | Python 3 + Flask (single file) | Bundled in the repo; no install beyond `pip install flask pyserial` |
| Frontend | Plain HTML + vanilla JS | No build step; opens in Safari/Chrome automatically |
| Communication | USB CDC serial via `pyserial` | Pico exposes a virtual serial port on macOS at `/dev/tty.usbmodem*` |
| Config sync | Write `/config.json` over serial file transfer | Hot reload — Pico picks up changes on next keypress |

### Launch Workflow
1. Plug in the Pico via USB
2. Run `python3 companion/app.py` (or a one-click `.command` file)
3. Flask starts on `http://localhost:5173` and opens automatically in the default browser
4. Visual 3×4 grid shows current labels on each key
5. Click any key cell → modal opens: change action type, shortcut chord, or macro text
6. Press **Save** → config written to Pico over serial; no reflash needed

### UI Screens
- **Grid view** — 3×4 visual layout, current label on each cell, hover shows full action
- **Key editor modal** — action type dropdown (`hid` / `macro`), chord/text input, "Test" button that fires the action live
- **Export / Import** — save current config as a named `.json` profile on the Mac; load it back any time

---

## 6. Hand-Wiring Guide

No PCB — all connections are point-to-point soldered.

**Per-key wiring:**
1. Solder one leg of a 1N4148 diode to the switch's top pin (cathode band facing away from the switch)
2. Connect the diode's anode to the row wire for that row
3. Connect the switch's other leg to the column wire for that column

**Matrix connections to Pico:**
- Row 0 → GPIO 2, Row 1 → GPIO 3, Row 2 → GPIO 4
- Col 0 → GPIO 6, Col 1 → GPIO 7, Col 2 → GPIO 8, Col 3 → GPIO 9
- Pico GND to common ground rail
- Pico USB to Mac

All wires can be standard 24–28 AWG solid or stranded hookup wire. Total solder joints: 12 switches × 2 legs + 12 diodes = ~36 joints plus 7 GPIO leads.

---

## 7. Open Source & Extensibility

- Full source on GitHub (MicroPython firmware + companion app)
- Developers can:
  - Edit `/config.json` directly on the Pico (mounts as USB mass storage when held in BOOTSEL)
  - Add custom action types in `actions/custom.py`
  - Replace the firmware entirely with KMK or CircuitPython
- `README.md` includes this wiring guide, the BOM, and step-by-step setup instructions

---

## 8. Bill of Materials

| Component | Qty | Est. Cost |
|-----------|-----|-----------|
| Raspberry Pi Pico | 1 | $4 |
| Outemu Red switches | 12 | ~$5 |
| 1N4148 diodes | 12 | $1 |
| Keycaps (◈ symbol on K12) | 12 | $4 |
| Perfboard | 1 | $2 |
| 3D-printed / laser-cut plate | 1 | $4–$8 |
| USB cable (Micro-USB or USB-C) | 1 | $2 |
| Hookup wire + solder | — | $2 |
| **Total** | | **~$24–$28** |

---

## 9. Deadline & Build Plan

**Deadline: 29 Aug, 3:00 PM**

| Time | Task |
|------|------|
| Now → 10 AM | Source all components locally (switches, Pico, diodes, perfboard) |
| 10 AM → 1 PM | Hand-wire the 3×4 matrix; test continuity |
| 1 PM → 4 PM | Flash MicroPython + write/test firmware (matrix scan, HID, macros) |
| 4 PM → 7 PM | Build companion UI (Flask + HTML grid view + key editor modal) |
| 7 PM → 10 PM | Integration test: all 12 keys working on macOS; STT via Dictation verified |
| 10 PM → 12 AM | Polish, README, and final demo prep |
| Morning 29 Aug | Buffer for fixes; submission by 3 PM |
