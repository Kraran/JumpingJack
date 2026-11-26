import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import unittest
from unittest.mock import patch
import pygame as pg
from main import Game,Hero,STEP
from support import finish_respawn
from savegame import capture,restore,validate


class PitDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def collide(self,lives=3,face=1):
        g=self.g;g.new_game();g.start_level(3);g.state='play';g.lives=lives
        g.hero=Hero(1800.,600.);g.hero.vy=140.;g.hero.face=face;g.invuln=100
        for _ in range(80):
            g.update(STEP,0,False,False)
            if g.hero_death.active:break
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'pit')
        self.assertLess(g.hero.y,640);self.assertFalse(g.resurrection.active)

    def test_visible_early_transition_continues_fall_and_locks_commands(self):
        g=self.g
        for face in (-1,1):
            self.collide(face=face);x,y=g.hero.x,g.hero.y;cam=g.cam
            for _ in range(30):g.update(STEP,1,True,True,fire=True,down=True)
            self.assertEqual(g.hero.x,x);self.assertGreater(g.hero.y,y);self.assertEqual(g.cam,cam)
            self.assertFalse(g.solar.active);self.assertFalse(g.hero.floating)
            self.assertEqual((g.lives,g.deaths),(2,1))
            finish_respawn(g);self.assertEqual((g.lives,g.deaths,g.state,g.energy.value),(2,1,'play',60))
        import tower_level
        g.new_game();g.start_level(4);g.state='play'
        g.hero=Hero(400,tower_level.BASE_Y+3);g.hero.vy=140
        g.update(STEP,0,False,False);self.assertEqual(g.hero_death.kind,'pit')
        g.prev_cam_y=g.cam_y-5
        g.update(STEP,0,False,False)
        self.assertEqual(g.prev_cam_y,g.cam_y)
        finish_respawn(g)

    def test_last_life_waits_and_rumbles_until_hero_disappears(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble:
            self.collide(lives=1);rumble.assert_called_once_with('death',duration=750)
            self.assertEqual(g.state,'play')
            finish_respawn(g);self.assertEqual(g.state,'game_over')
            self.assertAlmostEqual(g.hero_death.elapsed,.75)
            self.assertGreater(g.hero.y,720);self.assertEqual(rumble.call_args.args,('game_over',))

    def test_pause_save_restore_keep_the_panic_timeline(self):
        g=self.g;self.collide()
        for _ in range(25):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=copy.deepcopy(capture(g))
        for _ in range(10):g.update(STEP,1,True,True)
        self.assertEqual(capture(g),data);restore(g,data);self.assertEqual(capture(g),data)
        bad=copy.deepcopy(data);bad['hero_death']['elapsed']=.8
        with self.assertRaises(ValueError):validate(bad)
        with patch.object(g.gamepads,'rumble') as rumble:
            g.resume_from_menu();self.assertEqual(rumble.call_args.args,('death',))
            self.assertLess(rumble.call_args.kwargs['duration'],750)
        finish_respawn(g);self.assertEqual((g.lives,g.deaths),(2,1))

    def test_preloaded_transition_loop_and_mirrors_are_read_only(self):
        g=self.g;self.collide()
        with patch.object(pg.image,'load',side_effect=AssertionError('runtime load')),\
             patch.object(pg.transform,'smoothscale',side_effect=AssertionError('runtime scale')),\
             patch.object(pg.transform,'flip',side_effect=AssertionError('runtime mirror')):
            for i in range(80):
                g.hero_death.elapsed=i/79*.75;g.hero_death.previous_elapsed=max(0,g.hero_death.elapsed-STEP)
                for face in (-1,1):
                    g.hero_death.hero_face=face;before=copy.deepcopy(capture(g))
                    g.pit_death_sprites.draw(g.canvas,g.hero_death,g.hero,400,620,1,g.animation_bank.clips['fall'][0])
                    self.assertEqual(capture(g),before)
