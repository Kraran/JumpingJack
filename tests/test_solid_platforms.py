import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch,call
from main import Hero,Platform,Game,STEP


class SolidPlatformTests(unittest.TestCase):
    def test_sides_stop_hero_from_both_directions_even_with_large_step(self):
        wall=Platform(200,300,120,32)
        for direction in (-1,1):
            hero=Hero(100 if direction>0 else 420,340);hero.vx=340*direction
            hero.update(.4,direction,False,False,[wall])
            self.assertEqual(hero.x,185 if direction>0 else 335)
            self.assertEqual(hero.vx,0);self.assertTrue(hero.bump)

    def test_head_hits_nearest_underside_independently_of_platform_order(self):
        for platforms in ([Platform(0,200,500,32),Platform(0,300,500,32)],
                          [Platform(0,300,500,32),Platform(0,200,500,32)]):
            hero=Hero(100,410);hero.vy=-790
            hero.update(.1,0,False,False,platforms)
            self.assertEqual(hero.y,386);self.assertEqual(hero.vy,0)
            self.assertTrue(hero.bump)
            self.assertTrue(hero.head_bump);self.assertTrue(hero.glide_locked)

    def test_head_hit_blocks_glide_and_air_brake_until_landing(self):
        roof=Platform(0,300,500,32);floor=Platform(0,620,1000,100,True)
        hero=Hero(100,410);hero.vy=-790
        hero.update(.1,0,True,False,[roof,floor])
        self.assertTrue(hero.head_bump);self.assertTrue(hero.glide_locked)
        for tick in range(120):
            hero.update(STEP,0,True,tick%2==0,[roof,floor])
            if hero.grounded:break
            self.assertFalse(hero.floating);self.assertTrue(hero.glide_locked)
            self.assertGreater(hero.vy,0)
        self.assertTrue(hero.grounded);self.assertFalse(hero.glide_locked)

    def test_side_glide_impact_forces_fall_and_blocks_all_restarts_until_landing(self):
        wall=Platform(200,250,120,180);floor=Platform(0,620,1000,140,True)
        hero=Hero(184,350);hero.vx=340;hero.vy=105
        hero.update(STEP,1,True,False,[wall,floor])
        self.assertTrue(hero.glide_locked);self.assertFalse(hero.floating)
        self.assertGreater(hero.vy,105)
        for tick in range(100):
            hero.update(STEP,0,tick%2==0,tick%2==0,[wall,floor])
            self.assertFalse(hero.floating)
            if hero.grounded:break
            self.assertTrue(hero.glide_locked)
        self.assertTrue(hero.grounded);self.assertFalse(hero.glide_locked)
        hero.update(STEP,-1,True,True,[wall,floor])
        for _ in range(100):
            hero.update(STEP,-1,True,False,[wall,floor])
            if hero.floating:break
        self.assertTrue(hero.floating)

    def test_normal_side_collision_does_not_lock_future_glide(self):
        hero=Hero(184,350);hero.vx=340;hero.vy=200
        hero.update(STEP,1,False,False,[Platform(200,300,120,32)])
        self.assertTrue(hero.bump);self.assertFalse(hero.glide_locked)
        hero.update(STEP,0,True,False,[])
        self.assertTrue(hero.floating)

    def test_holding_wall_emits_one_bump_then_new_approach_emits_another(self):
        wall=Platform(200,300,120,100)
        hero=Hero(185,400);events=0
        for _ in range(20):
            hero.y=hero.py=400;hero.vy=0
            hero.update(STEP,1,False,False,[wall]);events+=hero.bump
        self.assertEqual(events,1)
        for _ in range(20):hero.update(STEP,-1,False,False,[])
        hero.x=185;hero.y=400;hero.vx=hero.vy=0
        hero.update(STEP,1,False,False,[wall])
        self.assertTrue(hero.bump)

    def test_deliberate_drop_ignores_source_until_entire_body_below_its_bottom(self):
        source=Platform(0,300,500,64);floor=Platform(0,620,1000,100,True)
        hero=Hero(250,300);hero.grounded=True
        hero.update(STEP,0,True,True,[source,floor],drop=True)
        for _ in range(100):
            hero.update(STEP,0,True,False,[source,floor])
            if hero.ignored_platform is source:self.assertLess(hero.y-hero.body_height,source.y+source.h+15)
            if hero.grounded and hero.y==620:break
        self.assertEqual(hero.y,620);self.assertIsNone(hero.ignored_platform)
        self.assertFalse(hero.bump)

    def test_crouch_cannot_stand_or_jump_through_low_ceiling(self):
        roof=Platform(0,550,300,32);floor=Platform(0,620,300,100,True)
        hero=Hero(100,620);hero.grounded=True;hero.crouch=hero.previous_crouch=1
        for _ in range(60):
            hero.update(STEP,0,False,True,[roof,floor])
            self.assertGreaterEqual(hero.y-hero.body_height,582)
            self.assertTrue(hero.grounded)


class SolidPlatformGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def test_side_impact_is_silent_and_reset_clears_glide_lock(self):
        self.g.reset();self.g.state='play';self.g.invuln=100
        self.g.hero=Hero(184,350);self.g.hero.vx=340;self.g.hero.vy=105
        self.g.platforms=[Platform(200,250,120,180)]
        with patch.object(self.g,'sound') as sound,patch.object(self.g.gamepads,'rumble') as rumble:
            self.g.update(STEP,1,True,False)
            sound.assert_not_called();rumble.assert_not_called()
        self.assertTrue(self.g.hero.glide_locked)
        self.g.reset();self.assertFalse(self.g.hero.glide_locked)

    def test_head_impact_plays_one_bong_and_one_rumble_even_with_sound_disabled(self):
        for sound_on in (False,True):
            self.g.reset();self.g.state='play';self.g.invuln=100;self.g.sound_on=sound_on
            self.g.hero=Hero(100,620);self.g.hero.grounded=True
            self.g.platforms=[Platform(0,500,500,32),Platform(0,620,1000,100,True)]
            with patch.object(self.g,'sound') as sound,patch.object(self.g.gamepads,'rumble') as rumble:
                for tick in range(90):self.g.update(STEP,0,True,tick==0)
                self.assertEqual(sound.call_args_list.count(call('bong')),1)
                rumble.assert_called_once_with('head_bump')


if __name__=='__main__':unittest.main()
