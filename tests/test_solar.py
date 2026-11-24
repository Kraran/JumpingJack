import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock, patch
import pygame as pg
from main import Hero, Game, Platform, STEP
from solar import SolarRay, WINDUP, BEAM_END, SHOT_TIME, FIRE_INTERVAL, BEAM_RANGE
from hero_animation import HeroAnimator, AnimationBank
from gamepad import ControllerPad, JoystickPad, Gamepads, PadButtons, PadSnapshot


class SolarTimingTests(unittest.TestCase):
    def test_preparation_emission_and_recovery_are_distinct(self):
        ray=SolarRay();hero=Hero();events=0
        for tick in range(48):
            events+=ray.update(STEP,hero,tick==0)
            if tick<16:self.assertFalse(ray.emitting)
            if 19<tick<33:self.assertTrue(ray.emitting)
            if tick>36:self.assertFalse(ray.emitting)
        self.assertEqual(events,1);self.assertFalse(ray.active)

    def test_repeat_presses_cannot_bypass_fire_interval(self):
        ray=SolarRay();hero=Hero()
        ray.update(STEP,hero,True)
        for _ in range(60):ray.update(STEP,hero,True)
        self.assertFalse(ray.active)
        for _ in range(20):ray.update(STEP,hero,True)
        self.assertTrue(ray.active)

    def test_ground_jump_and_fall_can_fire_but_glide_cannot(self):
        for grounded,vy in ((True,0),(False,-700),(False,500)):
            hero=Hero();hero.grounded=grounded;hero.vy=vy
            ray=SolarRay();ray.update(STEP,hero,True)
            self.assertTrue(ray.active)
        hero.floating=True;ray=SolarRay();ray.update(STEP,hero,True)
        self.assertFalse(ray.active)

    def test_glide_interrupts_existing_ray_without_queueing_another(self):
        hero=Hero();ray=SolarRay();ray.update(.2,hero,True)
        self.assertTrue(ray.emitting)
        hero.floating=True;ray.update(STEP,hero)
        self.assertFalse(ray.active)
        hero.floating=False;ray.update(1,hero)
        self.assertFalse(ray.active)

    def test_drop_and_heavy_recovery_block_firing(self):
        hero=Hero();hero.drop_elapsed=.1
        ray=SolarRay();ray.update(STEP,hero,True);self.assertFalse(ray.active)
        hero.drop_elapsed=None;hero.recovery=.6
        ray.update(STEP,hero,True);self.assertFalse(ray.active)

    def test_facing_is_committed_until_next_shot(self):
        hero=Hero();hero.face=-1;ray=SolarRay();ray.update(STEP,hero,True)
        hero.face=1;ray.update(STEP,hero)
        self.assertEqual(ray.facing,-1)

    def test_obstacles_stop_both_directions_without_blocking_from_behind(self):
        hero=Hero(1000,620);ray=SolarRay()
        right=Platform(1200,550,60,100);left=Platform(700,550,60,100)
        ray.facing=1
        self.assertEqual(ray.geometry(hero,[right,left])[2],1200)
        self.assertEqual(ray.geometry(hero,[left])[2],1034+BEAM_RANGE)
        ray.facing=-1
        self.assertEqual(ray.geometry(hero,[right,left])[2],760)

    def test_obstacle_containing_hands_produces_no_damage_area(self):
        hero=Hero(1000,620);ray=SolarRay()
        self.assertEqual(ray.bounds(hero,[Platform(1000,550,100,100)]).w,0)

    def test_solar_animation_covers_all_poses_and_switches_to_air_mid_shot(self):
        hero=Hero();hero.grounded=True;ray=SolarRay();animation=HeroAnimator()
        bank=AnimationBank({'solar_ground':list(range(8)),'solar_air':list(range(8)), 'fall':[0]})
        seen=[]
        for tick in range(47):
            ray.update(STEP,hero,tick==0);animation.update(STEP,hero,True,ray)
            seen.append(animation.sample(bank))
        self.assertEqual(sorted(set(seen)),list(range(8)))
        hero.grounded=False;hero.vy=-700
        animation.update(0,hero,True,ray)
        self.assertEqual(animation.state,'solar_air')
        self.assertEqual(animation.sample(bank),7)


class SolarMappingTests(unittest.TestCase):
    def test_b_is_separate_from_jump_on_both_backends(self):
        raw=MagicMock();raw.get_axis.return_value=0
        raw.get_button.side_effect=lambda button:button==pg.CONTROLLER_BUTTON_B
        sample=ControllerPad(raw).sample()
        self.assertTrue(sample.fire);self.assertFalse(sample.jump)
        raw.get_numaxes.return_value=0;raw.get_numhats.return_value=0
        raw.get_numbuttons.return_value=10
        raw.get_button.side_effect=lambda button:button==1
        sample=JoystickPad(raw).sample()
        self.assertTrue(sample.fire);self.assertFalse(sample.jump)

        # RT replaces jump on both SDL and generic Xbox layouts.
        raw.get_button.return_value=False;raw.get_button.side_effect=None
        raw.get_axis.side_effect=lambda axis:24000 if axis==pg.CONTROLLER_AXIS_TRIGGERRIGHT else 0
        controller=ControllerPad(raw)
        sample=controller.sample()
        self.assertTrue(sample.fire);self.assertFalse(sample.jump)
        pads=Gamepads(False);pads.devices={1:controller}
        self.assertTrue(pads.poll().fire_pressed)
        self.assertFalse(pads.poll().fire_pressed)
        raw.get_axis.side_effect=lambda axis:.8 if axis==5 else 0
        raw.get_numaxes.return_value=6
        sample=JoystickPad(raw).sample()
        self.assertTrue(sample.fire);self.assertFalse(sample.jump)
        raw.get_axis.side_effect=lambda axis:0
        sample=JoystickPad(raw).sample()
        self.assertFalse(sample.fire);self.assertFalse(sample.jump)

    def test_fire_is_an_edge_not_a_hold(self):
        pads=Gamepads(False);fake=MagicMock();fake.sample.return_value=PadButtons(fire=True)
        pads.devices={1:fake}
        self.assertTrue(pads.poll().fire_pressed)
        self.assertFalse(pads.poll().fire_pressed)
        fake.sample.return_value=PadButtons();pads.poll()
        fake.sample.return_value=PadButtons(fire=True)
        self.assertTrue(pads.poll().fire_pressed)


class SolarGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.game=Game(True)
    @classmethod
    def tearDownClass(cls):cls.game.close()
    def setUp(self):
        self.g=self.game;self.g.reset();self.g.state='play';self.g.invuln=10

    def fire(self):
        for tick in range(24):self.g.update(STEP,0,False,False,fire=tick==0)

    def test_ground_beam_kills_crocodile_in_front_but_not_behind(self):
        enemy=self.g.crocodiles[0]
        self.g.hero=Hero(700,620);self.g.hero.grounded=True
        self.fire();self.assertFalse(enemy.alive)
        self.assertFalse(enemy.hits(self.g.hero))
        self.g.reset();self.g.invuln=10
        self.g.hero=Hero(1200,620);self.g.hero.grounded=True
        self.fire();self.assertTrue(self.g.crocodiles[0].alive)

    def test_air_beam_kills_beetle_and_leaves_other_heights_alive(self):
        self.g.hero=Hero(1600,550)
        for tick in range(24):
            self.g.hero.y=self.g.hero.py=550;self.g.hero.vy=0
            self.g.update(STEP,0,False,False,fire=tick==0)
        self.assertIn(0,self.g.dead_beetles)
        self.assertNotIn(1,self.g.dead_beetles)
        self.assertEqual(len(self.g.enemy_positions()),5)

    def test_no_damage_during_charge_or_through_obstacle(self):
        self.g.hero=Hero(700,620);self.g.hero.grounded=True
        self.g.update(STEP,0,False,False,fire=True)
        self.assertTrue(self.g.crocodiles[0].alive)
        self.g.platforms.append(Platform(850,550,30,70))
        for _ in range(23):self.g.update(STEP,0,False,False)
        self.assertTrue(self.g.crocodiles[0].alive)

    def test_death_preserves_kills_and_clears_ray_restart_restores_enemies(self):
        self.g.crocodiles[0].alive=False;self.g.dead_beetles.add(0)
        self.g.solar.update(.2,self.g.hero,True)
        self.g.hero.y=900
        self.g.update(STEP,0,False,False)
        self.assertFalse(self.g.crocodiles[0].alive)
        self.assertEqual(self.g.dead_beetles,{0});self.assertFalse(self.g.solar.active)
        self.g.pending_fire=True;self.g.reset();self.assertFalse(self.g.pending_fire)
        self.assertTrue(self.g.crocodiles[0].alive);self.assertFalse(self.g.dead_beetles)

    def test_jump_and_b_can_be_pressed_together(self):
        self.g.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True,fire_pressed=True))
        self.assertTrue(self.g.pending_fire);self.assertTrue(self.g.pending_jump)
        self.g.update(STEP,0,True,True,fire=True)
        self.assertLess(self.g.hero.vy,0);self.assertTrue(self.g.solar.active)
        self.assertEqual(self.g.hero_animation.state,'solar_air')

    def test_b_does_not_fire_from_title_or_pause(self):
        for state in ('title','pause'):
            self.g.state=state;self.g.handle_pad(PadSnapshot(fire_pressed=True))
            self.assertFalse(self.g.pending_fire)

    def test_solar_draws_all_stages_without_readback(self):
        for tick in range(50):
            self.g.update(STEP,0,False,False,fire=tick==0)
            self.g.draw(.5)


if __name__=='__main__':unittest.main()
