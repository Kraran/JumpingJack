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
from desert_level import WATER_Y


class WaterDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def collide(self,vx=0,vy=600,lives=3):
        g=self.g;g.new_game();g.start_level(2);g.state='play';g.lives=lives
        g.hero=Hero(1150.,WATER_Y-2.);g.hero.vx=vx;g.hero.vy=vy;g.invuln=100
        for _ in range(60):
            g.update(STEP,0,False,False)
            if g.hero_death.active:break
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'water')
        self.assertFalse(g.hero.floating)

    def test_real_entry_keeps_momentum_sinks_and_costs_one_life(self):
        g=self.g
        for vx in (-340,0,340):
            for vy in (100,1200):
                self.collide(vx,vy);x,y=g.hero.x,g.hero.y
                for _ in range(40):g.update(STEP,-1,True,True,fire=True,down=True)
                self.assertGreater(g.hero.y,y)
                if vx:self.assertGreater((g.hero.x-x)*(1 if vx>0 else -1),0)
                self.assertFalse(g.solar.active);self.assertFalse(g.hero.floating)
                self.assertEqual((g.lives,g.deaths),(2,1))
                finish_respawn(g)
                self.assertEqual((g.lives,g.deaths,g.state,g.energy.value),(2,1,'play',60))

    def test_last_life_finishes_bite_and_submersion_before_game_over(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble:
            self.collide(lives=1);rumble.assert_called_once_with('water_entry',duration=550)
            for _ in range(200):g.update(STEP,0,False,False)
            self.assertEqual(g.state,'play');self.assertFalse(g.resurrection.active)
            finish_respawn(g)
            self.assertEqual(g.state,'game_over');self.assertAlmostEqual(g.hero_death.elapsed,2.6)
            self.assertEqual([c.args[0] for c in rumble.call_args_list],['water_entry','death','laser_fall','game_over'])
        with patch.object(g.native_canvas,'blit') as blit,patch.object(g.native_canvas,'blit_faded') as faded:
            g.water_death_sprites.draw(g.canvas,g.hero_death,g.hero,400,670,1,g.animation_bank)
            blit.assert_not_called();faded.assert_not_called()
        g.draw(1,present=False)

    def test_pause_save_and_reload_at_entry_bite_and_submersion(self):
        g=self.g
        for ticks in (20,110,245):
            self.collide()
            for _ in range(ticks):g.update(STEP,0,False,False)
            g.enter_menu('pause');data=copy.deepcopy(capture(g))
            for _ in range(10):g.update(STEP,1,True,True)
            self.assertEqual(capture(g),data)
            restore(g,data);self.assertEqual(capture(g),data)
            bad=copy.deepcopy(data);bad['hero_death']['x']=5000
            with self.assertRaises(ValueError):validate(bad)
            with patch.object(g.gamepads,'rumble') as rumble:
                g.resume_from_menu();self.assertTrue(rumble.called)
            finish_respawn(g);self.assertEqual((g.lives,g.deaths),(2,1))

    def test_rendering_uses_preloaded_cells_and_does_not_change_simulation(self):
        g=self.g;self.collide()
        with patch.object(pg.image,'load',side_effect=AssertionError('runtime load')),\
             patch.object(pg.transform,'smoothscale',side_effect=AssertionError('runtime scale')),\
             patch.object(pg.transform,'flip',side_effect=AssertionError('runtime mirror')):
            for i in range(80):
                g.hero_death.elapsed=i/79*2.6;g.hero_death.previous_elapsed=max(0,g.hero_death.elapsed-STEP)
                for face in (-1,1):
                    g.hero_death.hero_face=face;before=copy.deepcopy(capture(g))
                    g.water_death_sprites.draw(g.canvas,g.hero_death,g.hero,400,670,1,g.animation_bank)
                    self.assertEqual(capture(g),before)

    def test_bridge_posts_occlude_falling_hero_and_water_death_without_warning(self):
        g=self.g;g.new_game();g.start_level(2);g.state='play';g.invuln=100
        bridge=next(p for p in g.platforms if p.kind=='bridge')
        x=bridge.x+bridge.w*.92
        g.hero=Hero(x,WATER_Y-2);g.hero.vy=600
        g.cam=g.prev_cam=400.
        order=[]
        original_hero=g.draw_hero;original_front=g.desert_art.bridge_foreground
        def hero(*args,**kwargs):
            order.append('hero');return original_hero(*args,**kwargs)
        def front(*args,**kwargs):
            order.append('posts');return original_front(*args,**kwargs)
        with patch.object(g,'draw_hero',side_effect=hero),\
             patch.object(g.desert_art,'bridge_foreground',side_effect=front),\
             patch.object(g,'hud_notice') as notice:
            for dying in (False,True):
                if dying:g.update(STEP,0,False,False)
                g.cam=g.prev_cam=400.
                order.clear();g.draw(1,present=False)
                self.assertLess(order.index('hero'),order.index('posts'))
                px,py=g.canvas.point((x-400,620))
                self.assertEqual(tuple(g.native_canvas.surface.get_at((px,py)))[:3],(81,57,32))
                self.assertFalse(any('RIVIÈRE' in c.args[0] for c in notice.call_args_list))
