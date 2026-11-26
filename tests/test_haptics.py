import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock, patch
import pygame as pg
from gamepad import ControllerPad, JoystickPad, Gamepads, PadSnapshot, RUMBLE_EFFECTS
from main import Game, Hero, STEP


class RumbleDeviceTests(unittest.TestCase):
    def test_both_adapters_forward_both_motors_and_stop(self):
        for adapter in (ControllerPad,JoystickPad):
            raw=MagicMock();raw.rumble.return_value=True
            pad=adapter(raw)
            self.assertTrue(pad.rumble(.55,.25,170))
            raw.rumble.assert_called_once_with(.55,.25,170)
            pad.stop_rumble();raw.stop_rumble.assert_called_once()

    def test_no_controller_is_a_safe_noop(self):
        pads=Gamepads(False)
        self.assertFalse(pads.rumble('death'))
        pads.stop_rumble();pads.close()

    def test_unsupported_or_unplugged_device_does_not_block_other_pads(self):
        for failure in (pg.error('removed'),NotImplementedError(),AttributeError()):
            pads=Gamepads(False)
            bad=MagicMock();bad.rumble.side_effect=failure
            good=MagicMock();good.rumble.return_value=True
            detached=MagicMock();detached.attached.return_value=False
            pads.devices={1:bad,2:good,3:detached}
            self.assertTrue(pads.rumble('death'))
            good.rumble.assert_called_once_with(*RUMBLE_EFFECTS['death'])
            detached.rumble.assert_not_called()

    def test_device_that_reports_no_rumble_returns_false(self):
        pads=Gamepads(False);pad=MagicMock();pad.rumble.return_value=False
        pads.devices={1:pad}
        self.assertFalse(pads.rumble('land_heavy'))

    def test_close_stops_before_closing_device(self):
        pads=Gamepads(False);pad=MagicMock();pads.devices={1:pad}
        pads.close()
        self.assertEqual([c[0] for c in pad.mock_calls],['stop_rumble','close'])
        self.assertFalse(pads.devices)

    def test_refresh_does_not_quit_an_existing_generic_joystick(self):
        pads=Gamepads(False);raw=MagicMock()
        raw.get_instance_id.return_value=7;raw.get_init.return_value=True
        pads.devices={7:JoystickPad(raw)}
        with patch.object(pads,'_ensure',return_value=True),patch('gamepad.pg.joystick.get_count',return_value=1),patch('gamepad.pg.joystick.Joystick',return_value=raw):
            pads.refresh();pads.refresh()
        raw.quit.assert_not_called()
        self.assertTrue(pads.devices[7].attached())


class RumbleGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.game=Game(True)
    @classmethod
    def tearDownClass(cls):cls.game.close()

    def setUp(self):
        self.g=self.game;self.g.reset();self.g.state='play';self.g.invuln=10
        rumble=patch.object(self.g.gamepads,'rumble');self.rumble=rumble.start()
        self.addCleanup(rumble.stop)
        stop=patch.object(self.g.gamepads,'stop_rumble');self.stop=stop.start()
        self.addCleanup(stop.stop)

    def fall(self,height,glide=False):
        self.g.hero=Hero(100,620-height)
        for _ in range(500):
            self.g.update(STEP,0,glide,False)
            if self.g.hero.grounded:break

    def test_high_fall_pulses_once_at_contact_not_during_recovery(self):
        self.fall(320)
        self.rumble.assert_called_once_with('land_heavy')
        for _ in range(100):self.g.update(STEP,0,False,False)
        self.rumble.assert_called_once_with('land_heavy')

    def test_small_medium_and_gliding_landings_do_not_rumble(self):
        for height,glide in ((95,False),(200,False),(320,True)):
            self.fall(height,glide)
            self.rumble.assert_not_called()

    def test_pit_death_uses_stronger_effect_once(self):
        self.g.hero=Hero(100,900)
        self.g.update(STEP,0,False,False)
        self.rumble.assert_called_once_with('death',duration=750)
        self.assertEqual(self.g.deaths,1)
        self.g.update(STEP,0,False,False)
        self.rumble.assert_called_once_with('death',duration=750)
        low,high,duration=RUMBLE_EFFECTS['death']
        landing=RUMBLE_EFFECTS['land_heavy']
        self.assertGreater(low,landing[0]);self.assertGreater(high,landing[1])
        self.assertGreater(duration,landing[2])

    def test_death_at_contact_takes_priority_over_landing_rumble(self):
        self.g.invuln=0
        self.g.hero=Hero(300,619.5);self.g.hero.vy=600
        self.g.hero.fall_origin_y=300
        with patch.object(self.g,'enemy_positions',return_value=[(300,593)]):
            self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.deaths,1)
        self.rumble.assert_called_once_with('death')

    def test_pause_and_restart_stop_vibration(self):
        self.g.handle_pad(PadSnapshot(start_pressed=True))
        self.assertEqual(self.g.state,'pause')
        self.stop.assert_called_once()
        self.g.reset()
        self.assertEqual(self.stop.call_count,2)


if __name__=='__main__':unittest.main()
