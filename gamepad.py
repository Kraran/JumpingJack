"""Manettes SDL, avec un repli joystick à la disposition Xbox."""
from dataclasses import dataclass
import pygame as pg

try:
    import pygame._sdl2.controller as sdl_controller
except ImportError:
    sdl_controller = None

DEADZONE = 0.28
TRIGGER = 0.45
AXIS_MAX = 32767
RUMBLE_EFFECTS = {
    'land_heavy': (0.55, 0.25, 170),
    'death': (1.0, 1.0, 400),
    'head_bump': (0.35, 0.60, 110),
}


@dataclass(frozen=True)
class PadButtons:
    axis: int = 0
    jump: bool = False
    start: bool = False
    back: bool = False
    sound: bool = False
    down: bool = False
    fire: bool = False
    activity: bool = False


@dataclass(frozen=True)
class PadSnapshot:
    axis: int = 0
    jump_held: bool = False
    jump_pressed: bool = False
    start_pressed: bool = False
    back_pressed: bool = False
    sound_pressed: bool = False
    connected: bool = False
    name: str = ''
    down_held: bool = False
    fire_pressed: bool = False
    activity: bool = False


def stick_axis(raw, deadzone=DEADZONE):
    """Digitalise un axe. Les entiers SDL vont de -32768 à 32767."""
    value = float(raw) / AXIS_MAX if isinstance(raw, int) else float(raw)
    if value > deadzone:
        return 1
    if value < -deadzone:
        return -1
    return 0


def trigger_held(raw, threshold=TRIGGER):
    value = float(raw) / AXIS_MAX if isinstance(raw, int) else float(raw)
    return value > threshold


def merge_axis(*axes):
    total = sum(axes)
    if total > 0:
        return 1
    if total < 0:
        return -1
    return 0


class ControllerPad:
    def __init__(self, pad):
        self.pad = pad
        self.instance_id = pad.id
        self.name = pad.name or 'Manette'

    def attached(self):
        return bool(self.pad.attached())

    def sample(self):
        pad = self.pad
        stick = stick_axis(pad.get_axis(pg.CONTROLLER_AXIS_LEFTX))
        right = pad.get_button(pg.CONTROLLER_BUTTON_DPAD_RIGHT)
        left = pad.get_button(pg.CONTROLLER_BUTTON_DPAD_LEFT)
        axis = merge_axis(stick, 1 if right else -1 if left else 0)
        jump = bool(
            pad.get_button(pg.CONTROLLER_BUTTON_A)
            or pad.get_button(pg.CONTROLLER_BUTTON_DPAD_UP)
        )
        return PadButtons(
            axis,
            jump,
            bool(pad.get_button(pg.CONTROLLER_BUTTON_START)),
            bool(pad.get_button(pg.CONTROLLER_BUTTON_BACK)),
            bool(pad.get_button(pg.CONTROLLER_BUTTON_RIGHTSHOULDER)),
            stick_axis(pad.get_axis(pg.CONTROLLER_AXIS_LEFTY))>0
            or bool(pad.get_button(pg.CONTROLLER_BUTTON_DPAD_DOWN)),
            bool(pad.get_button(pg.CONTROLLER_BUTTON_B))
            or trigger_held(pad.get_axis(pg.CONTROLLER_AXIS_TRIGGERRIGHT)),
            any(pad.get_button(i) for i in range(pg.CONTROLLER_BUTTON_MAX))
            or any(stick_axis(pad.get_axis(i)) for i in range(4))
            or any(trigger_held(pad.get_axis(i)) for i in (pg.CONTROLLER_AXIS_TRIGGERLEFT,pg.CONTROLLER_AXIS_TRIGGERRIGHT)),
        )

    def close(self):
        self.pad.quit()

    def rumble(self, low, high, duration):
        return self.pad.rumble(low, high, duration)

    def stop_rumble(self):
        self.pad.stop_rumble()


class JoystickPad:
    """Disposition fréquente hors base SDL : axe 0, croix, boutons Xbox."""

    def __init__(self, joy):
        self.joy = joy
        self.instance_id = joy.get_instance_id()
        self.name = joy.get_name() or 'Manette'

    def attached(self):
        return bool(self.joy.get_init())

    def _button(self, index):
        return index < self.joy.get_numbuttons() and bool(self.joy.get_button(index))

    def sample(self):
        joy = self.joy
        stick = stick_axis(joy.get_axis(0)) if joy.get_numaxes() else 0
        hat_x = hat_y = 0
        if joy.get_numhats():
            hat_x, hat_y = joy.get_hat(0)
        trigger = trigger_held(joy.get_axis(5)) if joy.get_numaxes() > 5 else False
        return PadButtons(
            merge_axis(stick, hat_x),
            self._button(0) or hat_y > 0,
            self._button(7) or self._button(9),
            self._button(6) or self._button(8),
            self._button(5),
            hat_y<0 or (joy.get_numaxes()>1 and stick_axis(joy.get_axis(1))>0),
            self._button(1) or trigger,
            any(self._button(i) for i in range(joy.get_numbuttons()))
            or any(stick_axis(joy.get_axis(i)) for i in (0,1,3,4) if i<joy.get_numaxes())
            or bool(hat_x or hat_y) or trigger
            or (joy.get_numaxes()>2 and trigger_held(joy.get_axis(2))),
        )

    def close(self):
        self.joy.quit()

    def rumble(self, low, high, duration):
        return self.joy.rumble(low, high, duration)

    def stop_rumble(self):
        self.joy.stop_rumble()


class Gamepads:
    def __init__(self, autodetect=True):
        self.devices = {}
        self._held = {'jump': False, 'start': False, 'back': False, 'sound': False, 'fire': False}
        if autodetect:
            self.refresh()

    def _ensure(self):
        if not pg.get_init():
            return False
        try:
            if not pg.joystick.get_init():
                pg.joystick.init()
        except pg.error:
            return False
        if sdl_controller is not None and not sdl_controller.get_init():
            try:
                sdl_controller.init()
            except pg.error:
                pass
        return True

    def refresh(self):
        if not self._ensure():
            return
        found = {}
        for index in range(pg.joystick.get_count()):
            try:
                probe = pg.joystick.Joystick(index)
            except pg.error:
                continue
            found[probe.get_instance_id()] = (index, probe)
        for instance in list(self.devices):
            device = self.devices[instance]
            if instance not in found or not device.attached():
                self.devices.pop(instance)
                self._close(device)
        for instance, (index, probe) in found.items():
            if instance in self.devices:
                # pygame can return the very same Joystick object already held
                # by JoystickPad. Closing the probe would close the active pad.
                continue
            device = self._open(index, probe)
            if device is not None:
                self.devices[device.instance_id] = device

    def _open(self, index, probe):
        recognized = (
            sdl_controller is not None
            and sdl_controller.get_init()
            and sdl_controller.is_controller(index)
        )
        if not recognized:
            return JoystickPad(probe)
        probe.quit()
        try:
            return ControllerPad(sdl_controller.Controller(index))
        except pg.error:
            return None

    def poll(self):
        axis = 0
        jump = start = back = sound = down = fire = False
        connected = False
        activity = False
        name = ''
        for device in self.devices.values():
            try:
                if not device.attached():
                    continue
                sample = device.sample()
            except pg.error:
                continue
            connected = True
            name = name or device.name
            axis = merge_axis(axis, sample.axis)
            jump = jump or sample.jump
            start = start or sample.start
            back = back or sample.back
            sound = sound or sample.sound
            down = down or sample.down
            fire = fire or sample.fire
            activity = activity or sample.activity or bool(sample.axis or sample.jump or sample.start or sample.back or sample.sound or sample.down or sample.fire)
        snapshot = PadSnapshot(
            axis, jump,
            jump and not self._held['jump'],
            start and not self._held['start'],
            back and not self._held['back'],
            sound and not self._held['sound'],
            connected, name, down, fire and not self._held['fire'], activity,
        )
        self._held.update(jump=jump, start=start, back=back, sound=sound, fire=fire)
        return snapshot

    def rumble(self, event):
        effect = RUMBLE_EFFECTS[event]
        played = False
        for device in self.devices.values():
            try:
                if device.attached():
                    played = bool(device.rumble(*effect)) or played
            except (pg.error, AttributeError, NotImplementedError):
                pass
        return played

    def stop_rumble(self):
        for device in self.devices.values():
            self._stop(device)

    @staticmethod
    def _stop(device):
        try:
            device.stop_rumble()
        except (pg.error, AttributeError, NotImplementedError):
            pass

    def close(self):
        for device in self.devices.values():
            self._close(device)
        self.devices.clear()

    @staticmethod
    def _close(device):
        Gamepads._stop(device)
        try:
            device.close()
        except pg.error:
            pass
