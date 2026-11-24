import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
import pygame as pg
from gamepad import (
    ControllerPad, Gamepads, JoystickPad, PadButtons, PadSnapshot,
    merge_axis, stick_axis, trigger_held,
)
from main import Game, Hero, STEP


class AxisTests(unittest.TestCase):
    def test_deadzone_and_full_tilt(self):
        self.assertEqual(stick_axis(0),0)
        self.assertEqual(stick_axis(8000),0)
        self.assertEqual(stick_axis(-8000),0)
        self.assertEqual(stick_axis(12000),1)
        self.assertEqual(stick_axis(-12000),-1)
        self.assertEqual(stick_axis(32767),1)
        self.assertEqual(stick_axis(-32768),-1)

    def test_normalized_floats(self):
        self.assertEqual(stick_axis(0.2),0)
        self.assertEqual(stick_axis(0.5),1)
        self.assertEqual(stick_axis(-0.9),-1)

    def test_trigger_rest_is_not_a_press(self):
        self.assertFalse(trigger_held(0))
        self.assertFalse(trigger_held(-32768))
        self.assertTrue(trigger_held(20000))
        self.assertTrue(trigger_held(0.8))

    def test_opposite_directions_cancel(self):
        self.assertEqual(merge_axis(1,-1),0)
        self.assertEqual(merge_axis(-1,0),-1)
        self.assertEqual(merge_axis(1,1),1)


class _FakeController:
    def __init__(self):
        self.buttons={}
        self.axes={pg.CONTROLLER_AXIS_LEFTX:0,pg.CONTROLLER_AXIS_TRIGGERRIGHT:0}
        self.id=7
        self.name='Manette test'
        self.alive=True

    def attached(self):return self.alive
    def get_axis(self,axis):return self.axes.get(axis,0)
    def get_button(self,button):return self.buttons.get(button,0)
    def quit(self):self.alive=False


class MappingTests(unittest.TestCase):
    def test_standard_controller_buttons(self):
        raw=_FakeController()
        raw.axes[pg.CONTROLLER_AXIS_LEFTX]=-20000
        raw.buttons[pg.CONTROLLER_BUTTON_A]=1
        sample=ControllerPad(raw).sample()
        self.assertEqual(sample.axis,-1)
        self.assertTrue(sample.jump)
        self.assertFalse(sample.start)
        raw.buttons[pg.CONTROLLER_BUTTON_A]=0
        raw.buttons[pg.CONTROLLER_BUTTON_DPAD_RIGHT]=1
        raw.buttons[pg.CONTROLLER_BUTTON_START]=1
        raw.buttons[pg.CONTROLLER_BUTTON_RIGHTSHOULDER]=1
        raw.axes[pg.CONTROLLER_AXIS_LEFTX]=0
        sample=ControllerPad(raw).sample()
        self.assertEqual(sample.axis,1)
        self.assertTrue(sample.start)
        self.assertTrue(sample.sound)
        self.assertFalse(sample.jump)

    def test_generic_joystick_uses_xbox_indexes(self):
        class Joy:
            def get_instance_id(self):return 3
            def get_name(self):return 'Générique'
            def get_init(self):return True
            def get_numaxes(self):return 6
            def get_numbuttons(self):return 10
            def get_numhats(self):return 1
            def get_axis(self,index):return 0
            def get_button(self,index):return index in (6,9)
            def get_hat(self,index):return (-1,1)
            def quit(self):pass
        sample=JoystickPad(Joy()).sample()
        self.assertEqual(sample.axis,-1)
        self.assertTrue(sample.jump)
        self.assertTrue(sample.back)
        self.assertTrue(sample.start)

    def test_press_is_an_edge_and_hold_stays_down(self):
        class Fake:
            name='Test'
            def __init__(self):self.jump=False;self.axis=0
            def attached(self):return True
            def sample(self):return PadButtons(self.axis,self.jump,False,False,False)
            def close(self):pass
        fake=Fake()
        pads=Gamepads(autodetect=False)
        pads.devices[1]=fake
        fake.axis=1
        fake.jump=True
        first=pads.poll()
        second=pads.poll()
        self.assertTrue(first.jump_pressed)
        self.assertTrue(first.jump_held)
        self.assertEqual(first.axis,1)
        self.assertFalse(second.jump_pressed)
        self.assertTrue(second.jump_held)
        fake.jump=False
        pads.poll()
        fake.jump=True
        self.assertTrue(pads.poll().jump_pressed)


class GamepadGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):pg.quit()
    def setUp(self):self.g.reset();self.g.state='play';self.g.hero.grounded=True

    def test_jump_button_arms_one_jump(self):
        self.g.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True))
        self.assertTrue(self.g.pending_jump)
        self.g.update(STEP,0,True,self.g.pending_jump)
        self.assertLess(self.g.hero.vy,0)

    def test_start_pauses_and_a_resumes_without_jumping(self):
        self.g.handle_pad(PadSnapshot(start_pressed=True,jump_pressed=True,jump_held=True))
        self.assertEqual(self.g.state,'pause')
        self.assertFalse(self.g.pending_jump)
        self.g.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True))
        self.assertEqual(self.g.state,'play')
        self.assertFalse(self.g.pending_jump)

    def test_back_restarts_and_title_accepts_a(self):
        self.g.hero=Hero(4000,620)
        self.g.handle_pad(PadSnapshot(back_pressed=True))
        self.assertEqual(self.g.state,'play')
        self.assertEqual(self.g.hero.x,160)
        self.g.state='title'
        self.g.handle_pad(PadSnapshot(jump_pressed=True))
        self.assertEqual(self.g.state,'play')

    def test_shoulder_toggles_sound(self):
        self.assertTrue(self.g.sound_on)
        self.g.handle_pad(PadSnapshot(sound_pressed=True))
        self.assertFalse(self.g.sound_on)
        self.g.draw(1)
        self.g.state='title'
        self.g.pad=PadSnapshot(connected=True,name='Manette test')
        self.g.draw(1)
