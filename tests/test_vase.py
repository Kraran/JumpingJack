import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch
from main import Game,Hero,Platform,STEP
from vase import BREAK_TIME,SPAWNS
from savegame import capture,restore


class VaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        g=self.g;g.new_game();g.start_level(3);g.state='play';g.invuln=100

    def ray(self,x,face=1,crouch=False):
        g=self.g;g.hero=Hero(x,620);g.hero.grounded=True;g.hero.face=face
        g.solar.elapsed=.2;g.solar.powered=True;g.solar.facing=face;g.solar.crouched=crouch
        g.solar_hits()

    def test_solid_both_sides_and_can_be_jumped_over(self):
        g=self.g;vase=g.vases[0]
        for start,axis in ((740,1),(910,-1)):
            hero=Hero(start,620);hero.grounded=True
            for _ in range(100):hero.update(STEP,axis,False,False,g.collision_platforms())
            self.assertAlmostEqual(hero.x,vase.x-15 if axis>0 else vase.x+vase.w+15)
        hero=Hero(740,620);hero.grounded=True
        for tick in range(160):hero.update(STEP,1,False,tick==0,g.collision_platforms())
        self.assertGreater(hero.x,vase.x+vase.w+15)

    def test_standing_crouched_and_point_blank_rays_break_the_vase(self):
        for face,x in ((1,600),(-1,1030),(1,786),(-1,854)):
            for crouch in (False,True):
                self.g.vases[0].broken=False;self.g.solar.reset()
                self.ray(x,face,crouch);self.assertTrue(self.g.vases[0].broken,(x,face,crouch))

    def test_stone_occludes_vase_and_empty_or_charging_ray_does_not_break_it(self):
        g=self.g;g.hero=Hero(600,620);g.hero.face=1
        g.solar.elapsed=.1;g.solar.powered=True;g.solar_hits();self.assertFalse(g.vases[0].broken)
        g.solar.elapsed=.2;g.solar.powered=False;g.solar_hits();self.assertFalse(g.vases[0].broken)
        g.platforms.append(Platform(720,500,30,120,True))
        self.ray(600);self.assertFalse(g.vases[0].broken)

    def test_intact_vase_stops_ray_and_broken_one_clears_the_path(self):
        g=self.g;vase=g.vases[0];g.hero=Hero(600,620)
        before=g.solar.geometry(g.hero,g.collision_platforms())[2]
        self.assertEqual(before,vase.x);vase.shatter()
        after=g.solar.geometry(g.hero,g.collision_platforms())[2]
        self.assertGreater(after,vase.x+vase.w)
        self.assertNotIn(vase,g.collision_platforms())

    def test_broken_pottery_stays_broken_between_lives_and_save_load(self):
        g=self.g;g.vases[0].shatter();g.vases[0].update(.35)
        data=json.loads(json.dumps(capture(g)));restore(g,data)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)
        g.hero.y=900;g.update(STEP,0,False,False)
        self.assertEqual(g.lives,2);self.assertTrue(g.vases[0].broken)
        data=capture(g);del data['vases'];restore(g,data)
        self.assertEqual(len(g.vases),len(SPAWNS));self.assertFalse(g.vases[0].broken)

    def test_pottery_draws_preloaded_shards_without_mutation_or_transform(self):
        g=self.g;vase=g.vases[0];vase.shatter();vase.update(BREAK_TIME)
        before=dict(vars(vase))
        with patch('pygame.transform.rotozoom',side_effect=AssertionError('runtime rotation')),\
             patch('pygame.image.load',side_effect=AssertionError('runtime load')):
            for alpha in (0,.5,1):g.vase_sprites.draw(g.canvas,vase,300,alpha)
        self.assertEqual(vars(vase),before);self.assertEqual(vase.age,BREAK_TIME)
        self.assertFalse(vase.shatter())

    def test_vases_are_only_in_temple_and_new_run_restores_them(self):
        g=self.g;g.vases[0].shatter();g.start_level(3)
        self.assertFalse(g.vases[0].broken)
        for level in (1,2):g.start_level(level);self.assertEqual(g.vases,[])

    def test_settled_shards_rest_on_the_floor_instead_of_freezing_in_air(self):
        import pygame as pg
        sprites=self.g.vase_sprites
        from vase import BREAK_FRAMES
        i=BREAK_FRAMES-1
        frame=sprites.atlas.subsurface((i%8*240,i//8*180,240,180))
        parts=pg.mask.from_surface(frame,64).get_bounding_rects()
        self.assertTrue(parts)
        for part in parts:self.assertGreaterEqual(part.bottom,167)

    def test_old_four_vase_save_keeps_breakage_and_adds_supported_platform_vases(self):
        g=self.g;g.vases[0].shatter();data=capture(g);data['vases']=data['vases'][:4]
        restore(g,data)
        self.assertTrue(g.vases[0].broken);self.assertEqual(len(g.vases),7)
        for vase in g.vases[4:]:
            self.assertFalse(vase.broken)
            self.assertTrue(any(not p.ground and p.y==vase.floor and p.x<vase.x
                                and p.x+p.w>vase.x+vase.w for p in g.platforms))
