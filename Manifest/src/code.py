import time
import json
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

# ---------------------------------------------------------------------------
# Load configuration from config.json
# config.json sits alongside code.py on the CIRCUITPY drive root.
# ---------------------------------------------------------------------------
KEYCODE_MAP = {
    "A": Keycode.A, "B": Keycode.B, "C": Keycode.C, "D": Keycode.D,
    "E": Keycode.E, "F": Keycode.F, "G": Keycode.G, "H": Keycode.H,
    "I": Keycode.I, "J": Keycode.J, "K": Keycode.K, "L": Keycode.L,
    "M": Keycode.M, "N": Keycode.N, "O": Keycode.O, "P": Keycode.P,
    "Q": Keycode.Q, "R": Keycode.R, "S": Keycode.S, "T": Keycode.T,
    "U": Keycode.U, "V": Keycode.V, "W": Keycode.W, "X": Keycode.X,
    "Y": Keycode.Y, "Z": Keycode.Z,
    "0": Keycode.ZERO, "1": Keycode.ONE, "2": Keycode.TWO,
    "3": Keycode.THREE, "4": Keycode.FOUR, "5": Keycode.FIVE,
    "6": Keycode.SIX, "7": Keycode.SEVEN, "8": Keycode.EIGHT, "9": Keycode.NINE,
    "F1": Keycode.F1, "F2": Keycode.F2, "F3": Keycode.F3, "F4": Keycode.F4,
    "F5": Keycode.F5, "F6": Keycode.F6, "F7": Keycode.F7, "F8": Keycode.F8,
    "F9": Keycode.F9, "F10": Keycode.F10, "F11": Keycode.F11, "F12": Keycode.F12,
    "COMMAND": Keycode.COMMAND, "CTRL": Keycode.CONTROL, "CONTROL": Keycode.CONTROL,
    "ALT": Keycode.ALT, "SHIFT": Keycode.SHIFT,
    "ENTER": Keycode.ENTER, "RETURN": Keycode.ENTER,
    "ESCAPE": Keycode.ESCAPE, "ESC": Keycode.ESCAPE,
    "BACKSPACE": Keycode.BACKSPACE, "DELETE": Keycode.DELETE,
    "TAB": Keycode.TAB, "SPACE": Keycode.SPACE,
    "UP": Keycode.UP_ARROW, "DOWN": Keycode.DOWN_ARROW,
    "LEFT": Keycode.LEFT_ARROW, "RIGHT": Keycode.RIGHT_ARROW,
    "HOME": Keycode.HOME, "END": Keycode.END,
    "PAGE_UP": Keycode.PAGE_UP, "PAGE_DOWN": Keycode.PAGE_DOWN,
    "GRAVE_ACCENT": Keycode.GRAVE_ACCENT,
}

def parse_keystroke(keystroke_str):
    """Convert a '+'-separated string like 'COMMAND+SHIFT+B' into a list of Keycodes."""
    parts = [p.strip().upper() for p in keystroke_str.split("+")]
    return [KEYCODE_MAP[p] for p in parts if p in KEYCODE_MAP]

def load_config():
    try:
        with open("/config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print("Failed to load config.json:", e)
        return {"language": "Unknown", "keys": []}

def load_encoder_config():
    try:
        with open("/encoder.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print("Failed to load encoder.json:", e)
        return {
            "clockwise":         {"type": "language", "value": ""},
            "counter_clockwise": {"type": "language", "value": ""},
        }

# ---------------------------------------------------------------------------
# Language list — used by the "language" encoder action type
# ---------------------------------------------------------------------------
LANGUAGES = ["Python", "JavaScript", "Java", "C++", "C", "C#",
             "TypeScript", "Go", "Rust", "PHP"]

config = load_config()
enc_cfg = load_encoder_config()
lang = config.get("language", "Unknown")
lang_index = LANGUAGES.index(lang) if lang in LANGUAGES else 0
print("Language:", lang)

# Build COMMANDS list from enabled keys only (sorted by id)
raw_keys = sorted(config.get("keys", []), key=lambda k: k["id"])
COMMANDS = []
for k in raw_keys:
    if k.get("enabled", False):
        cmd = {"label": k.get("label", "Key"), "type": k.get("type", "macro")}
        if cmd["type"] in ("macro", "sequence"):
            cmd["type"] = "macro"
            cmd["sequence"] = k.get("sequence", "")
        elif cmd["type"] == "keystroke":
            cmd["type"] = "hid"
            cmd["keys"] = parse_keystroke(k.get("keystroke", ""))
        elif cmd["type"] == "hid":
            cmd["keys"] = parse_keystroke(k.get("keystroke", ""))
        elif cmd["type"] == "custom":
            cmd["type"] = "macro"
            cmd["sequence"] = k.get("custom_value", k.get("sequence", ""))
        COMMANDS.append(cmd)

print("Loaded", len(COMMANDS), "commands for", lang)

# ---------------------------------------------------------------------------
# Onboard LED
# ---------------------------------------------------------------------------
onboard_led = digitalio.DigitalInOut(board.LED)
onboard_led.direction = digitalio.Direction.OUTPUT

# ---------------------------------------------------------------------------
# Rotary encoder on GP16 (CLK) and GP17 (DT)
# ---------------------------------------------------------------------------
enc_clk = digitalio.DigitalInOut(board.GP16)
enc_clk.direction = digitalio.Direction.INPUT
enc_clk.pull = digitalio.Pull.UP

enc_dt = digitalio.DigitalInOut(board.GP17)
enc_dt.direction = digitalio.Direction.INPUT
enc_dt.pull = digitalio.Pull.UP

last_clk = enc_clk.value

# ---------------------------------------------------------------------------
# Button pins — GP0-GP5, GP7, GP8 (8 physical buttons)
# ---------------------------------------------------------------------------
BUTTON_PINS = [board.GP0, board.GP1, board.GP2, board.GP3,
               board.GP4, board.GP5, board.GP7, board.GP8]
buttons = []
for pin in BUTTON_PINS:
    btn = digitalio.DigitalInOut(pin)
    btn.direction = digitalio.Direction.INPUT
    btn.pull = digitalio.Pull.UP
    buttons.append(btn)

# ---------------------------------------------------------------------------
# HID keyboard
# ---------------------------------------------------------------------------
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

def run_command(command):
    if command["type"] == "hid":
        if command.get("keys"):
            kbd.press(*command["keys"])
            kbd.release_all()
    elif command["type"] == "macro":
        # Dismiss any open autocomplete popup before typing
        kbd.press(Keycode.ESCAPE)
        kbd.release_all()
        time.sleep(0.05)
        layout.write(command["sequence"])

def run_encoder_action(action):
    """Execute one encoder action dict from encoder.json."""
    global lang_index
    atype = action.get("type", "")
    value = action.get("value", "")

    if atype == "language":
        # Cycle to next/previous language — direction is baked in by
        # which action (cw vs ccw) calls this function
        pass  # lang_index already stepped before this is called
        print("Language:", LANGUAGES[lang_index])

    elif atype == "keystroke":
        keys = parse_keystroke(value)
        if keys:
            kbd.press(*keys)
            kbd.release_all()

    elif atype == "macro":
        kbd.press(Keycode.ESCAPE)
        kbd.release_all()
        time.sleep(0.05)
        layout.write(value)

    elif atype == "volume_up":
        # Consumer control not available in all CircuitPython builds;
        # fall back to a keystroke if defined in value
        if value:
            keys = parse_keystroke(value)
            if keys:
                kbd.press(*keys)
                kbd.release_all()

    elif atype == "volume_down":
        if value:
            keys = parse_keystroke(value)
            if keys:
                kbd.press(*keys)
                kbd.release_all()

    elif atype == "none":
        pass

prev_states = [True] * len(buttons)
led_state = False
last_led_toggle = time.monotonic()
LED_INTERVAL = 1.0

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
while True:
    now = time.monotonic()

    # Rotary encoder — run configured action
    clk = enc_clk.value
    dt  = enc_dt.value
    if clk != last_clk:
        if clk == False:            # falling edge = one detent
            if clk != dt:           # clockwise
                lang_index = (lang_index + 1) % len(LANGUAGES)
                run_encoder_action(enc_cfg.get("clockwise", {"type": "none"}))
            else:                   # counter-clockwise
                lang_index = (lang_index - 1) % len(LANGUAGES)
                run_encoder_action(enc_cfg.get("counter_clockwise", {"type": "none"}))
    last_clk = clk

    # Buttons
    for i, btn in enumerate(buttons):
        current_state = btn.value
        if prev_states[i] and not current_state:  # falling edge = press
            if i < len(COMMANDS):
                run_command(COMMANDS[i])
                onboard_led.value = True
                time.sleep(0.1)
                onboard_led.value = False
        prev_states[i] = current_state

    # LED heartbeat blink
    if now - last_led_toggle >= LED_INTERVAL:
        led_state = not led_state
        onboard_led.value = led_state
        last_led_toggle = now

    time.sleep(0.01)
