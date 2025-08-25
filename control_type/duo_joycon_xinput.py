from controllers.JoyconL import JoyConLeft
from controllers.JoyconR import JoyConRight

from dsu_server import controller_update

from config import Config
from pynput.mouse import Controller, Button

import vgamepad as vg
import threading
import time

# Initialize Joy-Con controllers
joyconLeft = JoyConLeft()
joyconRight = JoyConRight()

# Read the configuration from config.ini
config = Config().getConfig()

# Initialize virtual Xbox controller
gamepad = vg.VX360Gamepad()

# Initialize mouse loop at the start
firstCall = False

# Mouse movement variables
mouse = Controller()
targetX, targetY = 0, 0
previousMouseX, previousMouseY = 0, 0
leftPressed = False
rightPressed = False
joyconMouseMode = None

deadzone = config['joysticks_deadzone']

def mouse_loop():
    global targetX, targetY
    while True:
        stepX = targetX // 6
        stepY = targetY // 6
        if stepX != 0 or stepY != 0:
            mouse.move(stepX, stepY)
            targetX -= stepX
            targetY -= stepY
        time.sleep(0.006)
Controls = {}
# Button mapping: Joy-Con -> XInput
Controls["Left"] = config['custom_controls_left'] or {
        "ZL": "LEFT_TRIGGER",
        "L": "LEFT_SHOULDER",
        "L3": "LEFT_THUMB",
        "Right": "DPAD_RIGHT",
        "Down": "DPAD_DOWN",
        "Up": "DPAD_UP",
        "Left": "DPAD_LEFT",
        "Minus": "BACK",
        # "SLL", "SRL", "Capture" are unused
}
Controls["Right"] = config['custom_controls_right'] or {
        "ZR": "RIGHT_TRIGGER",
        "R": "RIGHT_SHOULDER",
        "R3": "RIGHT_THUMB",
        "A": "A",
        "B": "B",
        "X": "X",
        "Y": "Y",
        "Plus": "START",
        "Home": "GUIDE"
        # "SRR", "SLR", "GameChat" are unused
}
#print("Controls", Controls)
def clamp(value, min_value=-32768, max_value=32767):
    return max(min_value, min(max_value, value))
    
# Helper function to press/release XInput buttons
def set_button(button_name, pressed):
    # Special case
    if button_name == "LEFT_TRIGGER":
        if pressed:
            gamepad.left_trigger(255)
        else:
            gamepad.left_trigger(0)
        return
    if button_name == "RIGHT_TRIGGER":
        if pressed:
            gamepad.right_trigger(255)
        else:
            gamepad.right_trigger(0)
        return
        
    btn = getattr(vg.XUSB_BUTTON, "XUSB_GAMEPAD_" + button_name)
    if pressed:
        gamepad.press_button(btn)
    else:
        gamepad.release_button(btn)

def calculate_joystick_vals_alt(raw_x, raw_y):
    # Center joystick around 0
    cx = raw_x - 32767 // 2
    cy = raw_y - 32767 // 2

    # Calculate squared magnitude (faster than sqrt)
    mag_sq = cx * cx + cy * cy
    deadzone_sq = deadzone * deadzone

    if mag_sq < deadzone_sq:
        return 0, 0

    mag = int((mag_sq) ** 0.5)
    scale = (mag - deadzone) * 32767 // (16383 - deadzone)  # 16383 = 32767//2

    # Apply scale
    x = clamp(cx * scale // mag)
    y = clamp(-cy * scale // mag)  # Y inverted

    return x, y
def calculate_joystick_vals(raw_x, raw_y):
    # Calculate magnitude
    magnitude = (raw_x**2 + raw_y**2) ** 0.5
    if magnitude < deadzone:
        x, y = 0, 0
    else:
        scale = (magnitude - deadzone) / (32767 - deadzone)
        x = clamp(int(raw_x / magnitude * scale * 32767))
        y = clamp(int(-raw_y / magnitude * scale * 32767))  # Y inverted
    return x, y
async def update(controllerSide, joycon):
    global targetX, targetY, previousMouseX, previousMouseY
    global leftPressed, rightPressed, joyconMouseMode, firstCall

    isMouseMode = joycon.mouse["distance"] in ["00", "01"]

    if joyconMouseMode is None and isMouseMode and config['mouse_mode'] != 0:
        joyconMouseMode = controllerSide
    elif not isMouseMode and joyconMouseMode == controllerSide:
        joyconMouseMode = None

    if not firstCall and isMouseMode:
        threading.Thread(target=mouse_loop, daemon=True).start()
        firstCall = True

    # Set buttons
    for side in ["Left", "Right"]:
        for btnName, btnValue in Controls[side].items():
            pressed = False
            if side == "Left":
                pressed = joyconLeft.buttons.get(btnName, False) if side != joyconMouseMode else False
            else:
                pressed = joyconRight.buttons.get(btnName, False) if side != joyconMouseMode else False
            set_button(btnValue, pressed)
    
    # Set analog sticks
    if joyconMouseMode != "Left":
        # Get raw values
        data = calculate_joystick_vals_alt(joyconLeft.analog_stick["X"], joyconLeft.analog_stick["Y"])

        gamepad.left_joystick(x_value=data[0], y_value=data[1])
    if joyconMouseMode != "Right":
        # Get raw values
        data = calculate_joystick_vals_alt(joyconRight.analog_stick["X"], joyconRight.analog_stick["Y"])

        gamepad.right_joystick(x_value=data[0], y_value=data[1])

        if controllerSide == "Right" and config["enable_dsu"]:
            await controller_update(joyconRight.motionTimestamp, joyconRight.accelerometer, joyconRight.gyroscope)
    # Apply mouse movements if in mouse mode
    if isMouseMode and joyconMouseMode == controllerSide:
        deltaX = (joycon.mouse["X"] - previousMouseX + 32768) % 65536 - 32768
        deltaY = (joycon.mouse["Y"] - previousMouseY + 32768) % 65536 - 32768
        previousMouseX = joycon.mouse["X"]
        previousMouseY = joycon.mouse["Y"]
        targetX += deltaX
        targetY += deltaY

        # Mouse buttons
        if joycon.mouseBtn["Left"]:
            if not leftPressed:
                mouse.press(Button.left)
            leftPressed = True
        else:
            if leftPressed:
                mouse.release(Button.left)
            leftPressed = False

        if joycon.mouseBtn["Right"]:
            if not rightPressed:
                mouse.press(Button.right)
            rightPressed = True
        else:
            if rightPressed:
                mouse.release(Button.right)
            rightPressed = False

        mouse.scroll(joycon.mouseBtn["scrollX"] / 32768, joycon.mouseBtn["scrollY"] / 32768)

    gamepad.update()  # Send updates to virtual Xbox controller

async def notify_duo_joycons(client, side, data):
    if side == "Left":
        await joyconLeft.update(data)
        await update(side, joyconLeft)
    elif side == "Right":
        await joyconRight.update(data)
        await update(side, joyconRight)
    else:
        print("Unknown controller side.")
    return client
