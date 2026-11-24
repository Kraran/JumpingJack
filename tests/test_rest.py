import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock, patch
import pygame as pg
from rest import RestPose, IDLE_DELAY, REST_TIME
from main import Game, Hero, STEP
from gamepad import ControllerPad, JoystickPad, PadSnapshot


class RestTimingTests(unittest.TestCase):
    def test_starts_only_after_six_seconds(self):
        rest=RestPose();rest.update(5.999,False,True)
        self.assertFalse(rest.active)
        rest.update(.001,False,True)
        self.assertEqual(rest.state,'sitting')

    def test_seated_pose_waits_indefinitely_until_activity(self):
        rest=RestPose();rest.update(IDLE_DELAY,False,True)
        self.assertEqual(rest.state,'seated')
        for _ in range(30):rest.update(1,False,True)
        self.assertEqual(rest.progress,1)
        rest.update(STEP,True,True)
        self.assertEqual(rest.state,'rising');self.assertLess(rest.progress,1)

    def test_input_during_lowering_reverses_from_current_pose(self):
        rest=RestPose();rest.idle=IDLE_DELAY;rest.update(.1,False,True)
        before=rest.progress
        rest.update(STEP,True,True)
        self.assertEqual(rest.previous_progress,before)
        self.assertLess(rest.progress,before)
        self.assertGreater(rest.progress,0)

    def test_loss_of_support_cancels_pose(self):
        rest=RestPose();rest.update(7,False,True)
        rest.update(STEP,False,False)
        self.assertFalse(rest.active);self.assertEqual(rest.progress,0)

    def test_all_48_poses_are_sampled_and_reversed_with_common_clock(self):
        rest=RestPose();rest.idle=IDLE_DELAY;clip=list(range(48));seen=[]
        for _ in range(96):
            rest.update(STEP,False,True,-1);seen.append(rest.sample(clip))
        self.assertEqual(sorted(set(seen)),clip)
        self.assertEqual(rest.facing,-1)
        reverse=[]
        for _ in range(96):
            rest.update(STEP,True,True,1);reverse.append(rest.sample(clip))
        self.assertEqual(sorted(set(reverse)),clip)
        self.assertEqual(reverse,sorted(reverse,reverse=True))
        self.assertFalse(rest.active)

    def test_activity_prevents_sitting_while_a_control_is_held(self):
        rest=RestPose()
        for _ in range(1000):rest.update(STEP,True,True)
        self.assertEqual(rest.idle,0);self.assertFalse(rest.active)


class RestInputTests(unittest.TestCase):
    def test_unmapped_controller_button_and_right_stick_count_as_activity(self):
        raw=MagicMock();raw.get_button.side_effect=lambda button:button==pg.CONTROLLER_BUTTON_X
        raw.get_axis.return_value=0
        self.assertTrue(ControllerPad(raw).sample().activity)
        raw.get_button.return_value=False;raw.get_button.side_effect=None
        raw.get_axis.side_effect=lambda axis:20000 if axis==pg.CONTROLLER_AXIS_RIGHTX else 0
        self.assertTrue(ControllerPad(raw).sample().activity)

    def test_generic_trigger_rest_does_not_prevent_idle(self):
        raw=MagicMock();raw.get_numaxes.return_value=6;raw.get_numhats.return_value=0
        raw.get_numbuttons.return_value=10;raw.get_button.return_value=False
        raw.get_axis.side_effect=lambda axis:-1. if axis in (2,5) else 0.
        self.assertFalse(JoystickPad(raw).sample().activity)


class RestGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.game=Game(True)
    @classmethod
    def tearDownClass(cls):cls.game.close()
    def setUp(self):
        self.g=self.game;self.g.reset();self.g.state='play';self.g.invuln=10

    def seat(self):
        for _ in range(840):self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.rest.state,'seated')

    def test_six_seconds_then_seated_without_horizontal_drift(self):
        x=self.g.hero.x;self.seat()
        self.assertEqual(self.g.hero.x,x)
        self.assertEqual(self.g.hero_animation.state,'rest')

    def test_any_activity_wakes_without_moving(self):
        self.seat();x=self.g.hero.x
        self.g.update(STEP,0,False,False,activity=True)
        self.assertEqual(self.g.rest.state,'rising')
        for _ in range(100):self.g.update(STEP,0,False,False)
        self.assertFalse(self.g.rest.active);self.assertEqual(self.g.hero.x,x)

    def test_jump_wakes_without_jumping_and_requires_a_new_press(self):
        self.seat();self.g.update(STEP,0,True,True)
        self.assertTrue(self.g.hero.grounded)
        for _ in range(95):self.g.update(STEP,0,False,False)
        self.assertFalse(self.g.rest.active)
        self.assertTrue(self.g.hero.grounded)
        self.assertEqual(self.g.hero.vy,0)
        self.g.update(STEP,0,False,False)
        self.g.update(STEP,0,True,True)
        self.assertLess(self.g.hero.vy,0)

    def test_fire_wakes_without_shooting_and_requires_a_new_press(self):
        self.seat();self.g.update(STEP,0,False,False,fire=True)
        self.assertFalse(self.g.solar.active)
        for _ in range(95):self.g.update(STEP,0,False,False)
        self.assertFalse(self.g.solar.active)
        self.g.update(STEP,0,False,False)
        self.g.update(STEP,0,False,False,fire=True)
        self.assertTrue(self.g.solar.active)

    def test_pad_extra_button_wakes_and_reset_clears_history(self):
        self.seat();self.g.handle_pad(PadSnapshot(activity=True))
        self.g.update(STEP,0,False,False,activity=self.g.pending_activity)
        self.assertEqual(self.g.rest.state,'rising')
        self.g.reset();self.assertFalse(self.g.rest.active)
        self.assertFalse(self.g.pending_activity);self.assertFalse(self.g.wake_blocked)

    def test_airborne_or_recovering_hero_does_not_sit(self):
        for grounded,recovery in ((False,0),(True,.6)):
            self.g.reset();self.g.hero.grounded=grounded;self.g.hero.recovery=recovery
            self.g.rest.idle=5.999
            self.g.update(STEP,0,False,False)
            self.assertFalse(self.g.rest.active)

    def test_pause_freezes_seated_transition(self):
        self.seat();self.g.state='pause';before=self.g.rest.progress
        with patch.object(self.g,'close'),patch('main.pg.event.get',return_value=[]):
            self.g.run(frames=2)
        self.assertEqual(self.g.rest.progress,before)

    def test_unmapped_keyboard_key_wakes_through_event_loop(self):
        self.seat()
        event=pg.event.Event(pg.KEYDOWN,key=pg.K_j)
        with patch.object(self.g,'close'),patch('main.pg.event.get',side_effect=[[event],[]]):
            self.g.run(frames=2)
        self.assertEqual(self.g.rest.state,'rising')

    def test_held_direction_only_wakes_until_released(self):
        self.seat();x=self.g.hero.x
        for _ in range(130):self.g.update(STEP,1,False,False)
        self.assertFalse(self.g.rest.active)
        self.assertEqual(self.g.hero.x,x)
        self.g.update(STEP,0,False,False)
        self.g.update(STEP,1,False,False)
        self.assertGreater(self.g.hero.x,x)

    def test_pad_menu_and_sound_buttons_only_wake(self):
        for command in (PadSnapshot(start_pressed=True),PadSnapshot(back_pressed=True),PadSnapshot(sound_pressed=True)):
            self.g.reset();self.seat();sound=self.g.sound_on
            self.g.handle_pad(command)
            self.assertEqual(self.g.state,'play')
            self.assertEqual(self.g.sound_on,sound)
            self.g.update(STEP,0,False,False,activity=self.g.pending_activity)
            self.assertEqual(self.g.rest.state,'rising')

    def test_keyboard_sound_key_only_wakes(self):
        self.seat();sound=self.g.sound_on
        event=pg.event.Event(pg.KEYDOWN,key=pg.K_m)
        with patch.object(self.g,'close'),patch('main.pg.event.get',side_effect=[[event],[]]):
            self.g.run(frames=2)
        self.assertEqual(self.g.sound_on,sound)
        self.assertEqual(self.g.rest.state,'rising')

    def test_a_on_pad_is_consumed_as_wake_only(self):
        self.seat()
        self.g.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True,activity=True))
        self.assertFalse(self.g.pending_jump)
        self.g.update(STEP,0,True,False,activity=self.g.pending_activity)
        for _ in range(130):self.g.update(STEP,0,True,False)
        self.assertTrue(self.g.hero.grounded)
        self.assertFalse(self.g.rest.active)


if __name__=='__main__':unittest.main()
