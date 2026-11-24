import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
import pygame as pg
from main import Game,Hero,Platform,STEP
from hero_animation import CROUCH_TIME
from solar import MUZZLE_Y,CROUCH_MUZZLE_Y


class CrouchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        self.g.reset();self.g.state='play';self.g.invuln=100
        self.g.hero=Hero(100,620);self.g.hero.grounded=True

    def tick(self,down=True,fire=False,**kwargs):
        self.g.update(STEP,0,False,False,down=down,fire=fire,**kwargs)

    def lower(self):
        for _ in range(30):self.tick()

    def test_lower_hold_and_rise_are_progressive_and_grounded(self):
        self.tick();self.assertTrue(0<self.g.hero.crouch<1)
        self.lower();self.assertEqual(self.g.hero.crouch,1)
        self.assertEqual(self.g.hero_animation.state,'crouch')
        self.assertEqual(self.g.hero.rect.height,32)
        self.tick(down=False);self.assertTrue(0<self.g.hero.crouch<1)
        for _ in range(30):self.tick(down=False)
        self.assertEqual(self.g.hero.crouch,0)
        self.assertEqual(self.g.hero.rect.height,54)
        self.assertEqual((self.g.hero.x,self.g.hero.y),(100,620))

    def test_direction_aims_without_walking_while_crouched(self):
        self.lower();self.g.update(STEP,-1,False,False,down=True)
        self.assertEqual(self.g.hero.face,-1);self.assertEqual(self.g.hero.x,100)

    def test_airborne_down_does_not_crouch(self):
        self.g.hero=Hero(100,100)
        self.tick();self.assertEqual(self.g.hero.crouch,0)

    def test_down_jump_still_drops_from_platform(self):
        self.g.platforms=[Platform(0,300,500,32),Platform(0,620,500,100,True)]
        self.g.hero=Hero(100,300);self.g.hero.grounded=True;self.lower()
        self.g.update(STEP,0,True,True,drop=True,down=True)
        self.assertIsNotNone(self.g.hero.drop_elapsed)
        self.assertEqual(self.g.hero.crouch,0)
        self.assertEqual(self.g.hero_animation.state,'drop')

    def test_shot_while_lowering_waits_for_crouch_then_debits_once(self):
        self.tick(fire=True)
        self.assertFalse(self.g.solar.active);self.assertEqual(self.g.energy.value,100)
        for _ in range(29):self.tick()
        self.assertTrue(self.g.solar.active);self.assertTrue(self.g.solar.crouched)
        self.assertEqual(self.g.energy.value,70)
        self.assertEqual(self.g.hero_animation.state,'solar_crouch')

    def test_releasing_down_cancels_pending_crouch_shot(self):
        self.tick(fire=True);self.tick(down=False)
        for _ in range(60):self.tick(down=False)
        self.assertFalse(self.g.solar.active);self.assertEqual(self.g.energy.value,100)

    def test_crouched_ray_aims_lower_in_both_directions_and_stays_low(self):
        for facing in (-1,1):
            self.g.solar.reset();self.g.energy.reset();self.lower()
            self.g.hero.face=facing;self.tick(fire=True)
            target=pg.Rect(100+facing*160-5,590,10,10)
            self.assertTrue(self.g.solar.bounds(self.g.hero,[]).colliderect(target))
            self.assertEqual(self.g.solar.geometry(self.g.hero,[])[1],620-CROUCH_MUZZLE_Y)
            for _ in range(22):self.tick(down=False)
            self.assertEqual(self.g.hero.crouch,1)
            self.assertTrue(self.g.solar.emitting)
            for _ in range(60):self.tick(down=False)
            self.assertEqual(self.g.hero.crouch,0)
        self.g.solar.reset();self.tick(down=False,fire=True)
        self.assertEqual(self.g.solar.geometry(self.g.hero,[])[1],620-MUZZLE_Y)

    def test_dry_fire_uses_crouched_pose_without_emission(self):
        self.lower();self.g.energy.value=0;self.tick(fire=True)
        self.assertEqual(self.g.hero_animation.state,'solar_crouch')
        for _ in range(25):
            self.tick();self.assertFalse(self.g.solar.emitting)
        self.assertIsNone(self.g.solar.visual_elapsed)
        self.assertEqual(self.g.energy.value,0)

    def test_waking_with_down_only_raises_the_seated_hero(self):
        self.g.rest.state='seated';self.g.rest.progress=1
        for _ in range(120):self.tick()
        self.assertEqual(self.g.hero.crouch,0)
        self.tick(down=False);self.tick()
        self.assertGreater(self.g.hero.crouch,0)

    def test_pause_freezes_crouch_and_pending_shot(self):
        self.tick(fire=True);before=self.g.hero.crouch
        self.g.state='pause'
        with patch.object(self.g,'close'),patch('main.pg.event.get',return_value=[]):self.g.run(frames=2)
        self.assertEqual(self.g.hero.crouch,before);self.assertTrue(self.g.crouch_fire)

    def test_new_clips_sample_full_transition_without_render_side_effects(self):
        seen=[]
        for _ in range(30):
            self.tick();seen.append(self.g.hero_animation.sample(self.g.animation_bank))
        self.assertEqual(len(set(id(p) for p in seen)),8)
        before=self.g.hero.crouch
        for alpha in (0,.5,1):self.g.draw(alpha)
        self.assertEqual(self.g.hero.crouch,before)


if __name__=='__main__':unittest.main()
