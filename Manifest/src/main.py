import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

# Onboard LED
onboard_led = digitalio.DigitalInOut(board.LED)
onboard_led.direction = digitalio.Direction.OUTPUT

# GP0–GP3 each mapped to COMMANDS[0]–COMMANDS[3]
# Button wiring: connect each pin to GND via a momentary push button.
BUTTON_PINS = [board.GP0, board.GP1, board.GP2, board.GP3]
buttons = []
for pin in BUTTON_PINS:
    btn = digitalio.DigitalInOut(pin)
    btn.direction = digitalio.Direction.INPUT
    btn.pull = digitalio.Pull.UP
    buttons.append(btn)

# Set up HID keyboard + layout (layout needed for typing macro strings)
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

# ---------------------------------------------------------------------------
# Command definitions
# Each entry is either:
#   "hid"   — sends a key combo:      {"type": "hid",   "keys": [Keycode.X, ...]}
#   "macro" — types a text sequence:  {"type": "macro", "sequence": "some text\n"}
# ---------------------------------------------------------------------------
COMMANDS = [
    {"label": "Run",        "type": "hid",   "keys": [Keycode.F5]},
    {"label": "Build",      "type": "hid",   "keys": [Keycode.COMMAND, Keycode.SHIFT, Keycode.B]},
    {"label": "Copy",       "type": "hid",   "keys": [Keycode.COMMAND, Keycode.C]},
    {"label": "Paste",      "type": "hid",   "keys": [Keycode.COMMAND, Keycode.V]},
    {"label": "Git Commit", "type": "macro", "sequence": 'git commit -m "Testing"\n'},
    {"label": "Git Push",   "type": "macro", "sequence": "git push\n"},
    {"label": "Server",     "type": "macro", "sequence": "python3 -m http.server\n"},
    {"label": "New File",   "type": "hid",   "keys": [Keycode.COMMAND, Keycode.N]},
    {"label": "Terminal",   "type": "hid",   "keys": [Keycode.CONTROL, Keycode.GRAVE_ACCENT]},
    {"label": "Save All",   "type": "hid",   "keys": [Keycode.COMMAND, Keycode.ALT, Keycode.S]},
    {"label": "Format",     "type": "hid",   "keys": [Keycode.SHIFT, Keycode.ALT, Keycode.F]},
]

def run_command(command):
    """Execute a command dict from the COMMANDS array.

    Args:
        command: a dict with keys 'type' and either 'keys' (hid) or 'sequence' (macro)
    """
    if command["type"] == "hid":
        kbd.press(*command["keys"])
        kbd.release_all()
    elif command["type"] == "macro":
        layout.write(command["sequence"])

prev_states = [True] * len(buttons)  # True = not pressed (pulled high)
led_state = False
last_led_toggle = time.monotonic()
LED_INTERVAL = 1.0       # toggle LED every 1 second

while True:
    now = time.monotonic()
    # --- Buttons: GP0→COMMANDS[0], GP1→COMMANDS[1], GP2→COMMANDS[2], GP3→COMMANDS[3] ---
    for i, btn in enumerate(buttons):
        current_state = btn.value
        if prev_states[i] and not current_state:  # falling edge = press
            run_command(COMMANDS[i])
            onboard_led.value = True
            time.sleep(0.1)
            onboard_led.value = False
        prev_states[i] = current_state

    # --- LED blink: non-blocking, based on elapsed time ---
    if now - last_led_toggle >= LED_INTERVAL:
        led_state = not led_state
        onboard_led.value = led_state
        last_led_toggle = now

    time.sleep(0.01)     # short poll interval — responsive but not busy-looping