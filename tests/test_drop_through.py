import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock
import pygame as pg
from main import Hero, Platform, Game, STEP, ROOT
from hero_animation import HeroAnimator, AnimationBank, DROP_TIME, DROP_RELEASE
from gamepad import ControllerPad, JoystickPad, PadSnapshot, PadButtons, Gamepads


class DropPhysicsTests(unittest.TestCase):
    def setup_drop(self,gap=200):
        top=Platform(0,300,1000,32);lower=Platform(0,300+gap,1000,32)
        hero=Hero(500,300);hero.grounded=True
        return hero,[top,lower,Platform(0,700,1000,100,True)]

    def tick(self,hero,platforms,animation=None,held=True,pressed=False,drop=False,axis=0):
        was=hero.grounded
        hero.update(STEP,axis,held,pressed,platforms,drop=drop)
        if animation:animation.update(STEP,hero,was)

    def test_hand_preparation_stays_on_platform_then_moves_down(self):
        hero,plats=self.setup_drop();animation=HeroAnimator()
        self.tick(hero,plats,animation,pressed=True,drop=True)
        self.assertEqual(animation.state,'drop')
        for _ in range(19):self.tick(hero,plats,animation)
        self.assertTrue(hero.grounded);self.assertEqual(hero.y,300)
        for _ in range(3):self.tick(hero,plats,animation)
        self.assertFalse(hero.grounded);self.assertGreater(hero.y,300)
        self.assertGreater(hero.vy,0);self.assertFalse(hero.floating)
        self.assertIs(hero.ignored_platform,plats[0])

    def test_only_source_is_ignored_and_lower_platform_catches_held_button(self):
        for gap in (30,60,200,320):
            with self.subTest(gap=gap):
                hero,plats=self.setup_drop(gap)
                self.tick(hero,plats,pressed=True,drop=True)
                for _ in range(180):self.tick(hero,plats)
                self.assertTrue(hero.grounded)
                self.assertEqual(hero.y,300+gap)
                if hero.y-hero.body_height<plats[0].y+plats[0].h:
                    self.assertIs(hero.ignored_platform,plats[0])
                else:self.assertIsNone(hero.ignored_platform)
                self.assertIsNone(hero.drop_elapsed)

    def test_new_press_is_required_to_drop_again(self):
        hero,plats=self.setup_drop(60)
        self.tick(hero,plats,pressed=True,drop=True)
        for _ in range(100):self.tick(hero,plats)
        self.assertEqual(hero.y,360)
        self.tick(hero,plats,held=False)
        self.tick(hero,plats,pressed=True,drop=True)
        self.assertIsNotNone(hero.drop_elapsed)
        for _ in range(100):self.tick(hero,plats)
        self.assertEqual(hero.y,700)

    def test_solid_ground_cannot_be_dropped_through(self):
        hero=Hero(500,620);hero.grounded=True
        plats=[Platform(0,620,1000,100,True)]
        for tick in range(100):self.tick(hero,plats,pressed=tick==0,drop=True)
        self.assertEqual(hero.y,620);self.assertTrue(hero.grounded)
        self.assertIsNone(hero.drop_elapsed)

    def test_regular_jump_still_goes_up(self):
        hero,plats=self.setup_drop()
        self.tick(hero,plats,pressed=True)
        self.assertLess(hero.vy,0);self.assertLess(hero.y,300)

    def test_release_and_repress_after_drop_allows_gliding(self):
        hero,plats=self.setup_drop(320)
        self.tick(hero,plats,pressed=True,drop=True)
        for _ in range(43):self.tick(hero,plats)
        self.assertIsNone(hero.drop_elapsed)
        self.tick(hero,plats,held=False)
        self.tick(hero,plats,held=True,pressed=True)
        self.assertTrue(hero.floating)
        self.assertLessEqual(hero.vy,105)

    def test_recovery_prevents_drop_command(self):
        hero,plats=self.setup_drop();hero.recovery=.60
        self.tick(hero,plats,pressed=True,drop=True)
        self.assertIsNone(hero.drop_elapsed)
        self.assertEqual(hero.y,300)

    def test_drop_height_is_retained_for_reception(self):
        hero,plats=self.setup_drop(320);animation=HeroAnimator()
        self.tick(hero,plats,animation,pressed=True,drop=True)
        for _ in range(200):
            self.tick(hero,plats,animation)
            if hero.grounded and hero.y==620:break
        self.assertAlmostEqual(hero.landed_height,320)
        self.assertEqual(animation.state,'land_heavy')

    def test_all_drop_poses_play_in_order_and_override_turn(self):
        hero,plats=self.setup_drop(320);animation=HeroAnimator()
        bank=AnimationBank({'drop':list(range(12)),'fall':['fall'],'turn_ground':['turn']*8})
        seen=[]
        for tick in range(43):
            self.tick(hero,plats,animation,pressed=tick==0,drop=tick==0)
            animation.previous_turn=animation.turn=.75
            seen.append(animation.sample(bank))
            self.assertEqual(animation.render_facing(),-1)
        self.assertEqual(sorted(set(seen)),list(range(12)))
        self.assertEqual(seen,sorted(seen))
        self.tick(hero,plats,animation)
        self.assertEqual(animation.state,'fall')


class DropMappingTests(unittest.TestCase):
    def test_standard_pad_down_from_stick_and_dpad(self):
        raw=MagicMock();raw.get_button.return_value=False;raw.get_axis.return_value=0
        pad=ControllerPad(raw)
        self.assertFalse(pad.sample().down)
        raw.get_axis.side_effect=lambda axis:20000 if axis==pg.CONTROLLER_AXIS_LEFTY else 0
        self.assertTrue(pad.sample().down)
        raw.get_axis.side_effect=None;raw.get_axis.return_value=0
        raw.get_button.side_effect=lambda button:button==pg.CONTROLLER_BUTTON_DPAD_DOWN
        self.assertTrue(pad.sample().down)
        self.assertFalse(pad.sample().jump)

    def test_generic_pad_down_from_hat_and_axis(self):
        raw=MagicMock();raw.get_numaxes.return_value=2;raw.get_numhats.return_value=1
        raw.get_numbuttons.return_value=0;raw.get_axis.return_value=0
        raw.get_hat.return_value=(0,-1);pad=JoystickPad(raw)
        self.assertTrue(pad.sample().down)
        raw.get_hat.return_value=(0,0)
        raw.get_axis.side_effect=lambda axis:.8 if axis==1 else 0.
        self.assertTrue(pad.sample().down)

    def test_down_is_held_but_jump_keeps_its_press_edge(self):
        pads=Gamepads(False);raw=MagicMock();raw.sample.return_value=PadButtons(jump=True,down=True)
        pads.devices={1:raw}
        first=pads.poll();second=pads.poll()
        self.assertTrue(first.jump_pressed);self.assertTrue(first.down_held)
        self.assertFalse(second.jump_pressed);self.assertTrue(second.down_held)


class DropGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.game=Game(True)
    @classmethod
    def tearDownClass(cls):cls.game.close()

    def test_pad_command_reaches_physics_and_reset_clears_it(self):
        game=self.game;game.reset();game.state='play'
        game.hero=Hero(480,492);game.hero.grounded=True
        game.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True,down_held=True))
        self.assertTrue(game.pending_drop)
        game.update(STEP,0,True,game.pending_jump,game.pending_drop)
        self.assertEqual(game.hero_animation.state,'drop')
        self.assertEqual(game.hero.y,492)
        game.reset();self.assertFalse(game.pending_drop)
        self.assertIsNone(game.hero.drop_elapsed)

    def test_down_on_title_starts_without_dropping(self):
        game=self.game;game.reset();game.state='title'
        game.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True,down_held=True))
        self.assertEqual(game.state,'play')
        self.assertFalse(game.pending_drop)
        self.assertIsNone(game.hero.drop_elapsed)


if __name__=='__main__':unittest.main()
