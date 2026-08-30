"""
Macropad Configuration App
Requires: PyQt6, pyserial
Run:  /usr/bin/python3 app.py
"""

import json
import os
import sys
import time

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QGridLayout, QHBoxLayout,
    QVBoxLayout, QFrame, QMessageBox,
)

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# ─────────────────────────────────────────────────────────────────────────────
# Language list  (exactly the 10 requested)
# ─────────────────────────────────────────────────────────────────────────────
LANGUAGES = ["Python", "JavaScript", "Java", "C++", "C", "C#", "TypeScript", "Go", "Rust", "PHP"]

KEY_TYPES = ["macro", "keystroke", "sequence", "custom"]

TOTAL_KEYS   = 12
ENABLED_KEYS = 8
CONFIG_FILENAME   = "config.json"
ENCODER_FILENAME  = "encoder.json"

# "keystroke" is first/default — it reliably produces a felt result out of
# the box. "volume" and "language" are special: they're the two actions
# where clockwise and counter-clockwise deliberately do OPPOSITE things
# (volume up/down, next/previous language) rather than the same thing —
# see _save_encoder() below, which splits them per-direction on save.
ENCODER_ACTIONS = [
    ("keystroke",    "Keystroke"),
    ("macro",        "Type Text (macro)"),
    ("volume",       "Volume (turn up / turn down)"),
    # ("language",     "Cycle Language (turn to switch boilerplate)"),
    ("none",         "Do Nothing"),
]
ENCODER_ACTION_LABELS = [label for _, label in ENCODER_ACTIONS]
ENCODER_ACTION_TYPES  = [t     for t, _     in ENCODER_ACTIONS]

# Types that need a text value (keystroke string / macro text).
ENCODER_TYPES_NEEDING_VALUE = ("keystroke", "macro")

# ─────────────────────────────────────────────────────────────────────────────
# Per-language boilerplate presets  (8 keys each)
# Each entry: (label, type, sequence, keystroke)
# ─────────────────────────────────────────────────────────────────────────────
PRESETS = {
    "Python": [
        ("For Loop",    "macro", "for i in range():\n    ", ""),
        ("While",       "macro", "while True:\n    ", ""),
        ("Function",    "macro", "def func():\n    ", ""),
        ("Class",       "macro", "class MyClass:\n    def __init__(self):\n        ", ""),
        ("Try/Except",  "macro", "try:\n    \nexcept Exception as e:\n    print(e)\n", ""),
        ("Match",       "macro", "match value:\n    case 1:\n        pass\n    case _:\n        pass\n", ""),
        ("Open File",   "macro", "with open('file.txt') as f:\n    data = f.read()\n", ""),
        ("Print",       "macro", 'print("")', ""),
    ],
    "JavaScript": [
        ("For Loop",    "macro", "for (let i = 0; i < n; i++) {\n    \n}\n", ""),
        ("While",       "macro", "while (condition) {\n    \n}\n", ""),
        ("Function",    "macro", "function name() {\n    \n}\n", ""),
        ("Arrow Fn",    "macro", "const name = () => {\n    \n};\n", ""),
        ("Try/Catch",   "macro", "try {\n    \n} catch (e) {\n    console.error(e);\n}\n", ""),
        ("Switch",      "macro", "switch (val) {\n    case 1:\n        break;\n    default:\n        break;\n}\n", ""),
        ("Fetch",       "macro", "const res = await fetch('');\nconst data = await res.json();\n", ""),
        ("Console",     "macro", "console.log();", ""),
    ],
    "Java": [
        ("For Loop",    "macro", "for (int i = 0; i < n; i++) {\n    \n}\n", ""),
        ("While",       "macro", "while (condition) {\n    \n}\n", ""),
        ("Method",      "macro", "public void methodName() {\n    \n}\n", ""),
        ("Class",       "macro", "public class MyClass {\n    public MyClass() {\n    }\n}\n", ""),
        ("Try/Catch",   "macro", "try {\n    \n} catch (Exception e) {\n    e.printStackTrace();\n}\n", ""),
        ("Switch",      "macro", "switch (val) {\n    case 1:\n        break;\n    default:\n        break;\n}\n", ""),
        ("Sysout",      "macro", 'System.out.println("");', ""),
        ("Interface",   "macro", "public interface MyInterface {\n    void method();\n}\n", ""),
    ],
    "C++": [
        ("For Loop",    "macro", "for (int i = 0; i < n; i++) {\n    \n}\n", ""),
        ("While",       "macro", "while (condition) {\n    \n}\n", ""),
        ("Function",    "macro", "void funcName() {\n    \n}\n", ""),
        ("Class",       "macro", "class MyClass {\npublic:\n    MyClass() {}\n};\n", ""),
        ("Try/Catch",   "macro", "try {\n    \n} catch (const std::exception& e) {\n    std::cerr << e.what();\n}\n", ""),
        ("Switch",      "macro", "switch (val) {\n    case 1:\n        break;\n    default:\n        break;\n}\n", ""),
        ("Cout",        "macro", 'std::cout << "" << std::endl;', ""),
        ("Include",     "macro", "#include <iostream>\n", ""),
    ],
    "C": [
        ("For Loop",    "macro", "for (int i = 0; i < n; i++) {\n    \n}\n", ""),
        ("While",       "macro", "while (condition) {\n    \n}\n", ""),
        ("Function",    "macro", "void funcName() {\n    \n}\n", ""),
        ("Struct",      "macro", "typedef struct {\n    int field;\n} MyStruct;\n", ""),
        ("If/Else",     "macro", "if (condition) {\n    \n} else {\n    \n}\n", ""),
        ("Switch",      "macro", "switch (val) {\n    case 1:\n        break;\n    default:\n        break;\n}\n", ""),
        ("Printf",      "macro", 'printf("%s\\n", "");', ""),
        ("Include",     "macro", "#include <stdio.h>\n", ""),
    ],
    "C#": [
        ("For Loop",    "macro", "for (int i = 0; i < n; i++) {\n    \n}\n", ""),
        ("While",       "macro", "while (condition) {\n    \n}\n", ""),
        ("Method",      "macro", "public void MethodName() {\n    \n}\n", ""),
        ("Class",       "macro", "public class MyClass {\n    public MyClass() {\n    }\n}\n", ""),
        ("Try/Catch",   "macro", "try {\n    \n} catch (Exception e) {\n    Console.WriteLine(e.Message);\n}\n", ""),
        ("Switch",      "macro", "switch (val) {\n    case 1:\n        break;\n    default:\n        break;\n}\n", ""),
        ("Console",     "macro", 'Console.WriteLine("");', ""),
        ("Using",       "macro", "using System;\n", ""),
    ],
    "TypeScript": [
        ("For Loop",    "macro", "for (let i = 0; i < n; i++) {\n    \n}\n", ""),
        ("While",       "macro", "while (condition) {\n    \n}\n", ""),
        ("Function",    "macro", "function name(): void {\n    \n}\n", ""),
        ("Arrow Fn",    "macro", "const name = (): void => {\n    \n};\n", ""),
        ("Try/Catch",   "macro", "try {\n    \n} catch (e: unknown) {\n    console.error(e);\n}\n", ""),
        ("Interface",   "macro", "interface MyInterface {\n    field: string;\n}\n", ""),
        ("Type",        "macro", "type MyType = {\n    field: string;\n};\n", ""),
        ("Console",     "macro", "console.log();", ""),
    ],
    "Go": [
        ("For Loop",    "macro", "for i := 0; i < n; i++ {\n    \n}\n", ""),
        ("Range",       "macro", "for i, v := range items {\n    \n}\n", ""),
        ("Function",    "macro", "func name() {\n    \n}\n", ""),
        ("Struct",      "macro", "type MyStruct struct {\n    Field string\n}\n", ""),
        ("If Err",      "macro", "if err != nil {\n    return err\n}\n", ""),
        ("Switch",      "macro", "switch val {\ncase 1:\n    \ndefault:\n    \n}\n", ""),
        ("Fmt Print",   "macro", 'fmt.Println("")', ""),
        ("Goroutine",   "macro", "go func() {\n    \n}()\n", ""),
    ],
    "Rust": [
        ("For Loop",    "macro", "for i in 0..n {\n    \n}\n", ""),
        ("While",       "macro", "while condition {\n    \n}\n", ""),
        ("Function",    "macro", "fn name() {\n    \n}\n", ""),
        ("Struct",      "macro", "struct MyStruct {\n    field: String,\n}\n", ""),
        ("Match",       "macro", "match val {\n    1 => {},\n    _ => {},\n}\n", ""),
        ("If Let",      "macro", "if let Some(x) = option {\n    \n}\n", ""),
        ("Println",     "macro", 'println!("{}",  );', ""),
        ("Impl",        "macro", "impl MyStruct {\n    fn new() -> Self {\n        Self {}\n    }\n}\n", ""),
    ],
    "PHP": [
        ("For Loop",    "macro", "for ($i = 0; $i < $n; $i++) {\n    \n}\n", ""),
        ("Foreach",     "macro", "foreach ($items as $item) {\n    \n}\n", ""),
        ("Function",    "macro", "function name() {\n    \n}\n", ""),
        ("Class",       "macro", "class MyClass {\n    public function __construct() {\n    }\n}\n", ""),
        ("Try/Catch",   "macro", "try {\n    \n} catch (Exception $e) {\n    echo $e->getMessage();\n}\n", ""),
        ("Switch",      "macro", "switch ($val) {\n    case 1:\n        break;\n    default:\n        break;\n}\n", ""),
        ("Echo",        "macro", 'echo "";', ""),
        ("Array",       "macro", "$arr = [];\n", ""),
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Colours & stylesheets
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":           "#1e1e2e",
    "surface":      "#2a2a3d",
    "surface2":     "#313145",
    "border":       "#44445a",
    "accent":       "#7c5cd8",
    "accent_h":     "#9370e8",
    "text":         "#cdd6f4",
    "muted":        "#7f849c",
    "enabled_btn":  "#1e4d1a",
    "selected_btn": "#7c5cd8",
    "disabled_btn": "#2e2e3a",
    "connected":    "#a6e3a1",
    "disconnected": "#f38ba8",
}

SS_MAIN = f"""
QWidget {{
    background-color: {C["bg"]};
    color: {C["text"]};
    font-family: "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
}}
QLabel {{ background: transparent; }}
QFrame#vsep, QFrame#hsep {{ background-color: {C["border"]}; }}
"""

SS_COMBO = f"""
QComboBox {{
    background-color: {C["surface2"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 28px;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{
    width: 10px; height: 10px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {C["muted"]};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {C["surface2"]};
    color: {C["text"]};
    selection-background-color: {C["accent"]};
    selection-color: #ffffff;
    border: 1px solid {C["border"]};
    outline: none;
}}
"""

SS_INPUT = f"""
QLineEdit, QTextEdit {{
    background-color: {C["surface2"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    border-radius: 4px;
    padding: 5px 8px;
    font-family: "Courier New", monospace;
    font-size: 12px;
}}
QLineEdit:focus, QTextEdit:focus {{ border-color: {C["accent"]}; }}
QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {C["surface"]};
    color: {C["muted"]};
    border-color: {C["border"]};
}}
"""

SS_BTN_ACCENT = f"""
QPushButton {{
    background-color: {C["accent"]};
    color: #ffffff; border: none;
    border-radius: 5px; padding: 8px 18px; font-weight: bold;
}}
QPushButton:hover {{ background-color: {C["accent_h"]}; }}
QPushButton:pressed {{ background-color: #5a3fb8; }}
QPushButton:disabled {{ background-color: {C["surface2"]}; color: {C["muted"]}; }}
"""

SS_BTN_GREEN = f"""
QPushButton {{
    background-color: #347a28;
    color: #ffffff; border: none;
    border-radius: 5px; padding: 8px 18px; font-weight: bold;
}}
QPushButton:hover {{ background-color: #40a02b; }}
QPushButton:pressed {{ background-color: #256020; }}
"""

SS_BTN_SECONDARY = f"""
QPushButton {{
    background-color: {C["surface2"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    border-radius: 5px; padding: 8px 14px;
}}
QPushButton:hover {{ background-color: {C["border"]}; }}
QPushButton:pressed {{ background-color: {C["surface"]}; }}
"""

SS_BTN_PRESET = f"""
QPushButton {{
    background-color: #2a3a5c;
    color: {C["text"]};
    border: 1px solid #3a5080;
    border-radius: 5px; padding: 8px 14px; font-weight: bold;
}}
QPushButton:hover {{ background-color: #344a70; border-color: #4a6090; }}
QPushButton:pressed {{ background-color: #1e2a44; }}
"""

SS_KEY_ON = f"""
QPushButton {{
    background-color: {C["enabled_btn"]};
    color: {C["text"]};
    border: 1px solid #2d5a27;
    border-radius: 6px; font-size: 11px; padding: 6px 4px;
}}
QPushButton:hover {{ background-color: #26622a; border-color: #3a7232; }}
"""
SS_KEY_SEL = f"""
QPushButton {{
    background-color: {C["selected_btn"]};
    color: #ffffff;
    border: 2px solid {C["accent_h"]};
    border-radius: 6px; font-size: 11px; font-weight: bold; padding: 6px 4px;
}}
"""
SS_KEY_OFF = f"""
QPushButton {{
    background-color: {C["disabled_btn"]};
    color: {C["muted"]};
    border: 1px solid {C["border"]};
    border-radius: 6px; font-size: 11px; padding: 6px 4px;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────
def _blank_key(i: int) -> dict:
    return {
        "id": i, "label": f"Key {i}", "type": "macro",
        "sequence": "", "keystroke": "", "custom_value": "",
        "enabled": i < ENABLED_KEYS,
    }


def preset_keys_for(lang: str) -> list:
    """Return 12 key dicts built from the preset list for *lang*."""
    snippets = PRESETS.get(lang, [])
    keys = []
    for i in range(TOTAL_KEYS):
        k = _blank_key(i)
        if i < len(snippets):
            label, ktype, seq, ks = snippets[i]
            k.update({"label": label, "type": ktype, "sequence": seq, "keystroke": ks})
        keys.append(k)
    return keys


def default_config() -> dict:
    return {"language": "Python", "keys": preset_keys_for("Python")}


def load_config(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            existing = {k["id"]: k for k in data.get("keys", [])}
            keys = []
            for i in range(TOTAL_KEYS):
                if i in existing:
                    k = existing[i]
                    k.setdefault("custom_value", "")
                    keys.append(k)
                else:
                    keys.append(_blank_key(i))
            data["keys"] = sorted(keys, key=lambda x: x["id"])
            return data
        except Exception as e:
            QMessageBox.critical(None, "Config Error", f"Failed to load config:\n{e}")
    return default_config()


def save_config(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def default_encoder_config() -> dict:
    # Same action for both directions out of the box.
    action = {"label": "Keystroke", "type": "keystroke", "value": ""}
    return {
        "clockwise":         dict(action),
        "counter_clockwise": dict(action),
    }


def encoder_display_type(enc_data: dict) -> str:
    """Map the stored clockwise/counter_clockwise pair back to a single
    dropdown selection. volume_up/volume_down both mean "volume"."""
    cw_type = enc_data.get("clockwise", {}).get("type", "keystroke")
    if cw_type in ("volume_up", "volume_down"):
        return "volume"
    return cw_type


def load_encoder_config(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            QMessageBox.critical(None, "Encoder Config Error", f"Failed to load encoder.json:\n{e}")
    return default_encoder_config()


def find_pico_port():
    if not HAS_SERIAL:
        return None
    for port in serial.tools.list_ports.comports():
        combined = (port.description or "") + (port.hwid or "") + (port.manufacturer or "")
        if any(x in combined.lower() for x in ["circuitpython", "pico", "rp2040", "2e8a"]):
            return port.device
    return None


def find_pico_drive():
    import glob as _g
    for c in ["/Volumes/CIRCUITPY"]:
        if os.path.isdir(c):
            return c
    for p in _g.glob("/media/*/CIRCUITPY"):
        if os.path.isdir(p):
            return p
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Port-poll thread
# ─────────────────────────────────────────────────────────────────────────────
class PortPoller(QThread):
    status_changed = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        while self._running:
            port  = find_pico_port()
            drive = find_pico_drive()
            if port or drive:
                self.status_changed.emit(True, port or "USB drive")
            else:
                self.status_changed.emit(False, "Not connected")
            time.sleep(3)

    def stop(self):
        self._running = False
        self.wait(2000)


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────
class MacropadApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Macropad Configuration")
        self.setFixedSize(880, 700)
        self.setStyleSheet(SS_MAIN)

        self.config_path  = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME
        )
        self.encoder_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ENCODER_FILENAME
        )
        self.data         = load_config(self.config_path)
        self.enc_data     = load_encoder_config(self.encoder_path)
        self.selected_key_id = None
        self._suppressing    = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())
        root.addWidget(self._hsep())

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        bl.addWidget(self._build_left_panel())
        bl.addWidget(self._vsep())
        bl.addWidget(self._build_right_panel())
        root.addWidget(body, stretch=1)

        root.addWidget(self._hsep())
        root.addWidget(self._build_bottom_bar())

        self._refresh_grid()

        self._poller = PortPoller()
        self._poller.status_changed.connect(self._on_port_status)
        self._poller.start()

    def closeEvent(self, event):
        self._poller.stop()
        super().closeEvent(event)

    # ── Separators ────────────────────────────────────────────────────────────
    def _hsep(self):
        f = QFrame(); f.setObjectName("hsep")
        f.setFrameShape(QFrame.Shape.HLine); f.setFixedHeight(1)
        return f

    def _vsep(self):
        f = QFrame(); f.setObjectName("vsep")
        f.setFrameShape(QFrame.Shape.VLine); f.setFixedWidth(1)
        return f

    # ── Top bar ───────────────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = QWidget(); bar.setFixedHeight(52)
        bar.setStyleSheet(f"background:{C['surface']};")
        lay = QHBoxLayout(bar); lay.setContentsMargins(16, 0, 16, 0)

        lbl = QLabel("Language:"); lbl.setStyleSheet(f"color:{C['text']}; font-weight:bold;")
        lay.addWidget(lbl)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(LANGUAGES)
        self.lang_combo.setCurrentText(self.data.get("language", "Python"))
        self.lang_combo.setStyleSheet(SS_COMBO)
        self.lang_combo.setFixedWidth(160)
        # Connect AFTER initial setup to avoid spurious trigger
        self.lang_combo.currentTextChanged.connect(self._on_language_change)
        lay.addWidget(self.lang_combo)

        # Load presets button — right next to the dropdown
        self.load_preset_btn = QPushButton("↺  Load Boilerplate")
        self.load_preset_btn.setStyleSheet(SS_BTN_PRESET)
        self.load_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_preset_btn.setToolTip(
            "Replace all 8 key slots with the built-in boilerplate\n"
            "for the selected language."
        )
        self.load_preset_btn.clicked.connect(self._load_preset)
        lay.addWidget(self.load_preset_btn)

        lay.addStretch()

        lbl2 = QLabel("Macropad:"); lbl2.setStyleSheet(f"color:{C['muted']}; font-size:12px;")
        lay.addWidget(lbl2)
        self.status_dot = QLabel("●"); self.status_dot.setStyleSheet(f"color:{C['disconnected']}; font-size:16px;")
        lay.addWidget(self.status_dot)
        self.status_label = QLabel("Not connected"); self.status_label.setStyleSheet(f"color:{C['disconnected']}; font-size:12px;")
        lay.addWidget(self.status_label)
        return bar

    # ── Left panel: grid + encoder config ────────────────────────────────────
    def _build_left_panel(self):
        panel = QWidget(); panel.setFixedWidth(380)
        lay = QVBoxLayout(panel); lay.setContentsMargins(16, 14, 16, 14); lay.setSpacing(10)

        title = QLabel("Key Layout  (3 × 4)")
        title.setStyleSheet(f"color:{C['text']}; font-size:14px; font-weight:bold;")
        lay.addWidget(title)

        hint = QLabel("First 8 keys are active  ·  Click a key to configure it")
        hint.setStyleSheet(f"color:{C['muted']}; font-size:11px;")
        lay.addWidget(hint)

        gw = QWidget(); self.grid_layout = QGridLayout(gw); self.grid_layout.setSpacing(8)
        self.key_buttons = []
        for i in range(TOTAL_KEYS):
            row, col = divmod(i, 3)
            btn = QPushButton(f"Key {i}")
            btn.setFixedSize(100, 68)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._select_key(idx))
            self.grid_layout.addWidget(btn, row, col)
            self.key_buttons.append(btn)
        lay.addWidget(gw)

        # ── Encoder configuration section ─────────────────────────────────
        # A single action fires no matter which way the knob turns — the
        # UI used to expose separate clockwise/counter-clockwise rows,
        # but the two were almost always set to the same thing anyway.
        lay.addWidget(self._hsep())

        enc_title = QLabel("Rotary Encoder")
        enc_title.setStyleSheet(f"color:{C['text']}; font-size:13px; font-weight:bold; margin-top:4px;")
        lay.addWidget(enc_title)

        enc_hint = QLabel("Same action both ways — except Volume & Language, which go up/down or next/previous")
        enc_hint.setStyleSheet(f"color:{C['muted']}; font-size:11px;")
        lay.addWidget(enc_hint)

        lay.addWidget(self._mlabel("Action"))

        row_w = QWidget()
        row_l = QHBoxLayout(row_w); row_l.setContentsMargins(0, 0, 0, 0); row_l.setSpacing(6)

        combo = QComboBox(); combo.addItems(ENCODER_ACTION_LABELS)
        combo.setStyleSheet(SS_COMBO); combo.setFixedWidth(180)
        cur_type = encoder_display_type(self.enc_data)
        if cur_type in ENCODER_ACTION_TYPES:
            combo.setCurrentIndex(ENCODER_ACTION_TYPES.index(cur_type))
        row_l.addWidget(combo)

        val_edit = QLineEdit()
        val_edit.setStyleSheet(SS_INPUT)
        val_edit.setPlaceholderText("value / keystroke")
        # Only keystroke/macro carry a text value — volume and language
        # are handled natively on-device and don't need one.
        if cur_type in ENCODER_TYPES_NEEDING_VALUE:
            val_edit.setText(self.enc_data.get("clockwise", {}).get("value", ""))
        val_edit.setFixedWidth(140)
        row_l.addWidget(val_edit)

        lay.addWidget(row_w)

        self._enc_combo = combo
        self._enc_value = val_edit

        # Show/hide the value field based on the selected action type
        def _toggle_val(idx, ve=val_edit):
            ve.setVisible(ENCODER_ACTION_TYPES[idx] in ENCODER_TYPES_NEEDING_VALUE)
        combo.currentIndexChanged.connect(_toggle_val)
        _toggle_val(combo.currentIndex())   # set initial visibility

        save_enc_btn = QPushButton("Save Encoder Config")
        save_enc_btn.setStyleSheet(SS_BTN_ACCENT)
        save_enc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_enc_btn.clicked.connect(self._save_encoder)
        lay.addWidget(save_enc_btn)

        lay.addStretch()
        return panel

    # ── Right panel: key config ───────────────────────────────────────────────
    def _build_right_panel(self):
        panel = QWidget()
        lay = QVBoxLayout(panel); lay.setContentsMargins(16, 14, 16, 14); lay.setSpacing(6)

        title = QLabel("Key Configuration")
        title.setStyleSheet(f"color:{C['text']}; font-size:14px; font-weight:bold;")
        lay.addWidget(title)

        lay.addWidget(self._mlabel("Key Name"))
        self.key_name_edit = QLineEdit(); self.key_name_edit.setStyleSheet(SS_INPUT)
        self.key_name_edit.setPlaceholderText("e.g.  For Loop"); self.key_name_edit.setEnabled(False)
        lay.addWidget(self.key_name_edit)

        lay.addWidget(self._mlabel("Key Type"))
        self.type_combo = QComboBox(); self.type_combo.addItems(KEY_TYPES)
        self.type_combo.setStyleSheet(SS_COMBO); self.type_combo.setEnabled(False)
        self.type_combo.currentTextChanged.connect(self._sync_fields)
        lay.addWidget(self.type_combo)

        # Sequence row
        sr = QHBoxLayout()
        sr.addWidget(self._mlabel("Sequence / Value"))
        sr.addStretch()
        sr.addWidget(self._hint('e.g.  for i in range():\\n'))
        lay.addLayout(sr)
        self.seq_edit = QTextEdit(); self.seq_edit.setStyleSheet(SS_INPUT)
        self.seq_edit.setFixedHeight(72); self.seq_edit.setEnabled(False)
        self.seq_edit.textChanged.connect(self._sync_fields)
        lay.addWidget(self.seq_edit)

        # Keystroke row
        kr = QHBoxLayout()
        kr.addWidget(self._mlabel("Keystroke"))
        kr.addStretch()
        kr.addWidget(self._hint('e.g.  COMMAND+SHIFT+B'))
        lay.addLayout(kr)
        self.ks_edit = QLineEdit(); self.ks_edit.setStyleSheet(SS_INPUT)
        self.ks_edit.setPlaceholderText("COMMAND+SHIFT+B"); self.ks_edit.setEnabled(False)
        self.ks_edit.textChanged.connect(self._sync_fields)
        lay.addWidget(self.ks_edit)

        lay.addWidget(self._mlabel("Custom Value (raw override)"))
        self.custom_edit = QLineEdit(); self.custom_edit.setStyleSheet(SS_INPUT)
        self.custom_edit.setPlaceholderText("Any raw string — overrides sequence & keystroke")
        self.custom_edit.setEnabled(False)
        self.custom_edit.textChanged.connect(self._sync_fields)
        lay.addWidget(self.custom_edit)

        self.mutex_label = QLabel(""); self.mutex_label.setStyleSheet(f"color:{C['muted']}; font-size:11px;")
        self.mutex_label.setWordWrap(True); lay.addWidget(self.mutex_label)

        lay.addStretch()

        self.save_key_btn = QPushButton("Save Key"); self.save_key_btn.setStyleSheet(SS_BTN_ACCENT)
        self.save_key_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_key_btn.setEnabled(False); self.save_key_btn.clicked.connect(self._save_key)
        lay.addWidget(self.save_key_btn)
        return panel

    # ── Bottom bar ────────────────────────────────────────────────────────────
    def _build_bottom_bar(self):
        bar = QWidget(); bar.setFixedHeight(40)
        bar.setStyleSheet(f"background:{C['surface']};")
        lay = QHBoxLayout(bar); lay.setContentsMargins(16, 0, 16, 0)

        lay.addStretch()
        self.status_bar = QLabel("Ready"); self.status_bar.setStyleSheet(f"color:{C['muted']}; font-size:12px;")
        lay.addWidget(self.status_bar)
        return bar

    # ── Small helpers ─────────────────────────────────────────────────────────
    def _mlabel(self, t: str) -> QLabel:
        l = QLabel(t); l.setStyleSheet(f"color:{C['muted']}; font-size:12px; margin-top:4px;"); return l

    def _hint(self, t: str) -> QLabel:
        l = QLabel(t); l.setStyleSheet(f"color:{C['muted']}; font-family:'Courier New'; font-size:11px;"); return l

    def _set_status(self, msg: str):
        self.status_bar.setText(msg)
        QTimer.singleShot(4000, lambda: self.status_bar.setText("Ready"))

    # ── Grid refresh ──────────────────────────────────────────────────────────
    def _refresh_grid(self):
        keys = self.data.get("keys", [])
        for i, btn in enumerate(self.key_buttons):
            k       = keys[i] if i < len(keys) else {}
            label   = k.get("label", f"Key {i}")
            enabled = k.get("enabled", False)
            sel     = (i == self.selected_key_id)
            btn.setText(label)
            btn.setStyleSheet(SS_KEY_SEL if sel else SS_KEY_ON if enabled else SS_KEY_OFF)

    # ── Key selection ─────────────────────────────────────────────────────────
    def _select_key(self, idx: int):
        self.selected_key_id = idx
        self._refresh_grid()
        keys = self.data.get("keys", [])
        k    = keys[idx] if idx < len(keys) else {}

        self._suppressing = True
        self.key_name_edit.setText(k.get("label", f"Key {idx}"))
        ktype = k.get("type", "macro")
        self.type_combo.setCurrentText(ktype if ktype in KEY_TYPES else "macro")
        self.seq_edit.setPlainText(k.get("sequence", ""))
        self.ks_edit.setText(k.get("keystroke", ""))
        self.custom_edit.setText(k.get("custom_value", ""))
        self._suppressing = False

        for w in [self.key_name_edit, self.type_combo,
                  self.seq_edit, self.ks_edit, self.custom_edit, self.save_key_btn]:
            w.setEnabled(True)
        self._sync_fields()

    # ── Field mutual-exclusion sync ───────────────────────────────────────────
    def _sync_fields(self):
        if self._suppressing or self.selected_key_id is None:
            return
        ktype  = self.type_combo.currentText()
        seq    = self.seq_edit.toPlainText().strip()
        ks     = self.ks_edit.text().strip()
        custom = self.custom_edit.text().strip()

        if custom:
            self._inp(self.seq_edit, False); self._inp(self.ks_edit, False)
            self.mutex_label.setText("Custom value active — sequence & keystroke ignored.")
            return
        if ktype in ("macro", "sequence"):
            self._inp(self.seq_edit, True); self._inp(self.ks_edit, not bool(seq))
            self.mutex_label.setText("Sequence active — keystroke disabled." if seq else "")
        elif ktype == "keystroke":
            self._inp(self.ks_edit, True); self._inp(self.seq_edit, not bool(ks))
            self.mutex_label.setText("Keystroke active — sequence disabled." if ks else "")
        elif ktype == "custom":
            self._inp(self.seq_edit, False); self._inp(self.ks_edit, False)
            self.mutex_label.setText("Use the Custom Value field above.")
        else:
            self._inp(self.seq_edit, True); self._inp(self.ks_edit, True)
            self.mutex_label.setText("")

    def _inp(self, w, enabled: bool):
        w.setEnabled(enabled)
        w.setStyleSheet(SS_INPUT if enabled else
                        SS_INPUT.replace(C["surface2"], C["surface"])
                                .replace(C["text"], C["muted"]))

    # ── Language change & preset loader ──────────────────────────────────────
    def _on_language_change(self, lang: str):
        if not self._suppressing:
            self.data["language"] = lang

    def _load_preset(self):
        lang = self.lang_combo.currentText()
        answer = QMessageBox.question(
            self, "Load Boilerplate",
            f"Replace all 8 key slots with the built-in {lang} boilerplate\nand push to Pico?\n\n"
            "Any unsaved edits will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.data["language"] = lang
        self.data["keys"]     = preset_keys_for(lang)
        self.selected_key_id  = None
        self._refresh_grid()
        # Clear & disable the right panel
        self._suppressing = True
        self.key_name_edit.clear()
        self.seq_edit.clear()
        self.ks_edit.clear()
        self.custom_edit.clear()
        self._suppressing = False
        for w in [self.key_name_edit, self.type_combo,
                  self.seq_edit, self.ks_edit, self.custom_edit, self.save_key_btn]:
            w.setEnabled(False)
        self.mutex_label.setText("")
        self._export_to_pico(silent=True)

    # ── Port status ───────────────────────────────────────────────────────────
    def _on_port_status(self, connected: bool, label: str):
        col = C["connected"] if connected else C["disconnected"]
        self.status_dot.setStyleSheet(f"color:{col}; font-size:16px;")
        self.status_label.setStyleSheet(f"color:{col}; font-size:12px;")
        self.status_label.setText(label if connected else "Not connected")

    # ── Save key ──────────────────────────────────────────────────────────────
    def _save_key(self):
        if self.selected_key_id is None:
            return
        idx  = self.selected_key_id
        keys = self.data.get("keys", [])
        while len(keys) <= idx:
            keys.append(_blank_key(len(keys)))
        k = keys[idx]
        k["label"]        = self.key_name_edit.text().strip() or f"Key {idx}"
        k["type"]         = self.type_combo.currentText()
        k["sequence"]     = self.seq_edit.toPlainText()
        k["keystroke"]    = self.ks_edit.text().strip()
        k["custom_value"] = self.custom_edit.text().strip()
        self.data["keys"] = keys
        self._refresh_grid()
        self._export_to_pico(silent=True)

    # ── Save encoder config ───────────────────────────────────────────────────
    def _save_encoder(self):
        """Commit the single encoder action → enc_data, then push to Pico.

        Most action types fire identically in both directions. "volume"
        and "language" are the two deliberate exceptions: clockwise and
        counter-clockwise get opposite variants (up/down, next/previous)
        so the knob behaves the way you'd expect a volume/scroll knob to.
        """
        idx    = self._enc_combo.currentIndex()
        atype  = ENCODER_ACTION_TYPES[idx]
        alabel = ENCODER_ACTION_LABELS[idx]
        aval   = self._enc_value.text().strip()

        if atype in ENCODER_TYPES_NEEDING_VALUE and not aval:
            QMessageBox.warning(
                self, "Missing Value",
                f'"{alabel}" needs a value (e.g. a keystroke like COMMAND+SHIFT+B,\n'
                "or text for a macro) or turning the encoder will do nothing."
            )
            return

        if atype == "volume":
            self.enc_data = {
                "clockwise":         {"label": "Volume Up",   "type": "volume_up",   "value": ""},
                "counter_clockwise": {"label": "Volume Down", "type": "volume_down", "value": ""},
            }
        elif atype == "language":
            self.enc_data = {
                "clockwise":         {"label": "Next Language",     "type": "language", "value": ""},
                "counter_clockwise": {"label": "Previous Language", "type": "language", "value": ""},
            }
        else:
            action = {"label": alabel, "type": atype, "value": aval}
            self.enc_data = {
                "clockwise":         dict(action),
                "counter_clockwise": dict(action),
            }

        save_config(self.encoder_path, self.enc_data)
        self._export_to_pico(silent=True)
        self._set_status(f"✓ Encoder action set: {alabel}")

    # ── Export to Pico ────────────────────────────────────────────────────────
    def _export_to_pico(self, silent: bool = False):
        """Write config.json + encoder.json (and optionally code.py) to CIRCUITPY."""
        drive = find_pico_drive()
        if not drive:
            self._set_status("Pico not found — connect and try again.")
            if not silent:
                QMessageBox.warning(
                    self, "Pico Not Found",
                    "CIRCUITPY drive not detected.\nPlug in the Pico and try again."
                )
            return

        src_code = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "Manifest", "src", "code.py"
        )
        try:
            save_config(os.path.join(drive, CONFIG_FILENAME),  self.data)
            save_config(os.path.join(drive, ENCODER_FILENAME), self.enc_data)
            save_config(self.config_path,  self.data)
            save_config(self.encoder_path, self.enc_data)
            copied_code = False
            if os.path.exists(src_code):
                import shutil
                shutil.copy2(src_code, os.path.join(drive, "code.py"))
                copied_code = True
            detail = "config.json + encoder.json" + (" + code.py" if copied_code else "")
            self._set_status(f"✓ Pushed {detail} to Pico")
            if not silent:
                QMessageBox.information(
                    self, "Export Success",
                    f"{detail} written to:\n{drive}\n\nThe Pico will reload on next boot."
                )
        except Exception as e:
            self._set_status(f"Export failed: {e}")
            QMessageBox.critical(self, "Export Error", str(e))


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(C["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(C["surface2"]))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(C["surface"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(C["surface2"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(C["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)

    window = MacropadApp()
    window.show()
    sys.exit(app.exec())