import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import unittest
from unittest.mock import patch
import pygame as pg
from main import Game,Hero,STEP
from savegame import capture,restore,validate
from support import finish_respawn
from fire_death import pose_position,extinction
import tower_level


class FireDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def collide(self,level=3,lives=3):
        g=self.g;g.new_game();g.start_level(level);g.state='play';g.lives=lives
        x,y=(650.,390.) if level==3 else tower_level.TORCHES[0]
        g.hero=Hero(x,y);g.invuln=100
        g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'fire')
        return x,y

    def test_real_fire_contacts_in_both_levels_cost_one_life_and_ignore_inputs(self):
        g=self.g
        for level in (3,4):
            with self.subTest(level=level):
                self.collide(level);y=g.hero.y
                for _ in range(45):g.update(STEP,1,True,True,fire=True,down=True)
                self.assertGreater(g.hero.y,y);self.assertFalse(g.hero.floating);self.assertFalse(g.solar.active)
                self.assertEqual((g.lives,g.deaths),(2,1))
                g.draw(1,present=False)
                finish_respawn(g)
                self.assertEqual((g.lives,g.deaths,g.state,g.energy.value),(2,1,'play',60))

    def test_air_pose_holds_until_landing_then_collapses_before_resurrection(self):
        g=self.g;self.collide()
        with patch.object(g.hero,'update'):
            for _ in range(216):g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertIsNone(g.hero_death.landed_at)
        self.assertEqual(pose_position(g.hero_death,g.hero_death.elapsed),7)
        while g.hero_death.active:g.update(STEP,0,False,False)
        death=g.hero_death
        self.assertGreaterEqual(death.elapsed,death.landed_at+1.-1e-9)
        self.assertEqual(pose_position(death,death.elapsed),15)
        self.assertAlmostEqual(extinction(death,death.elapsed),1)
        self.assertTrue(g.resurrection.active)
        finish_respawn(g)
        # A body lost through a pit must also extinguish before Game Over.
        from temple_level import FLOORS
        self.collide(lives=1)
        g.hero=Hero((FLOORS[0][1]+FLOORS[1][0])/2,650.)
        finish_respawn(g)
        self.assertEqual(g.state,'game_over')
        self.assertIsNotNone(g.hero_death.landed_at)
        self.assertAlmostEqual(extinction(g.hero_death,g.hero_death.elapsed),1.)

    def test_last_life_waits_and_vibration_weakens_before_game_over(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble:
            self.collide(lives=1)
            rumble.assert_called_once_with('death',duration=120)
            self.assertEqual((g.state,g.lives),('play',0))
            finish_respawn(g)
            events=[call.args[0] for call in rumble.call_args_list]
            self.assertIn('fire_burn',events);self.assertIn('fire_flicker',events);self.assertIn('fire_embers',events)
            self.assertEqual(events[-1],'game_over');self.assertEqual(g.state,'game_over')
        with patch.object(g.fire_death_sprites,'draw',wraps=g.fire_death_sprites.draw) as draw:
            g.draw(1,present=False);draw.assert_called_once()

    def test_pause_save_restore_and_remaining_burn_feedback(self):
        g=self.g;self.collide()
        for _ in range(105):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=copy.deepcopy(capture(g))
        for _ in range(10):g.update(STEP,1,True,True)
        self.assertEqual(capture(g),data)
        restore(g,data);self.assertEqual(capture(g),data)
        bad=copy.deepcopy(data);bad['hero_death']['landed_at']=bad['hero_death']['elapsed']+1
        with self.assertRaises(ValueError):validate(bad)
        with patch.object(g.gamepads,'rumble') as rumble:
            g.resume_from_menu();self.assertTrue(rumble.called)
        finish_respawn(g);self.assertEqual((g.lives,g.deaths),(2,1))

    def test_all_phases_both_facings_draw_without_loading_or_transforming(self):
        g=self.g;self.collide();death=g.hero_death
        with patch.object(pg.image,'load',side_effect=AssertionError('runtime load')),\
             patch.object(pg.transform,'smoothscale',side_effect=AssertionError('runtime scale')),\
             patch.object(pg.transform,'flip',side_effect=AssertionError('runtime mirror')):
            for i in range(65):
                death.elapsed=i/64*1.6;death.previous_elapsed=max(0.,death.elapsed-STEP)
                death.landed_at=.6 if death.elapsed>=.6 else None
                for face in (-1,1):
                    death.hero_face=face;before=copy.deepcopy(capture(g))
                    g.fire_death_sprites.draw(g.canvas,death,g.hero,350,620,1)
                    self.assertEqual(capture(g),before)

    def test_continuous_fire_covers_each_body_pose_and_has_mirrored_envelopes(self):
        from laser_death import CELL
        sprites=self.g.fire_death_sprites
        for pose in range(16):
            key=round(pose/15*63)
            body=pg.mask.from_surface(sprites.images[0].subsurface((key%8*CELL[0],key//8*CELL[1],*CELL)),100)
            for phase in range(8):
                key=pose*8+phase;area=(key%8*CELL[0],key//8*CELL[1],*CELL)
                right=sprites.envelopes[0].subsurface(area)
                fire=pg.mask.from_surface(right,12)
                self.assertGreater(body.overlap_area(fire,(0,0))/body.count(),.95)
                left=sprites.envelopes[1].subsurface(area)
                self.assertEqual(pg.image.tobytes(left,'RGBA'),pg.image.tobytes(pg.transform.flip(right,True,False),'RGBA'))

    def test_atlas_fading_restores_alpha_without_changing_pixels(self):
        from gpu_render import NativeCanvas
        canvas=NativeCanvas();image=pg.Surface((8,8),pg.SRCALPHA);image.fill((255,0,0,255))
        before=pg.image.tobytes(image,'RGBA');alpha=image.get_alpha()
        canvas.surface.fill((0,0,0));canvas.blit_faded(image,(0,0),(0,0,8,8),128)
        self.assertAlmostEqual(canvas.surface.get_at((2,2)).r,128,delta=1)
        self.assertEqual(image.get_alpha(),alpha);self.assertEqual(pg.image.tobytes(image,'RGBA'),before)
        canvas.blit_faded(image,(8,0),(0,0,8,8),255)
        self.assertEqual(canvas.surface.get_at((10,2)).r,255)
