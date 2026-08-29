import usb_hid
import storage
import usb_cdc

# Disable the CIRCUITPY USB mass storage drive.
# This prevents macOS from showing the "Disk Not Ejected Properly" error
# when HID keystrokes (e.g. Cmd+Space) are sent.
storage.disable_usb_drive()

# Disable the serial console (optional — remove this line if you need
# to see print() output in Thonny/mpremote for debugging)
# usb_cdc.disable()

# Enable HID (keyboard) — this is on by default but stated explicitly for clarity
usb_hid.enable(usb_hid.BOOT_DEVICE_KEYBOARD)
