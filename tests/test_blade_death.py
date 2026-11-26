import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from spikes import teeth,SPIKE_DEPTH
from savegame import capture,restore,validate
from support import finish_respawn


class BladeDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def collide(self,level=1,lives=3,face=1):
        g=self.g;g.new_game();g.start_level(level);g.state='play';g.lives=lives;g.invuln=100
        platform=next(p for p in g.platforms if p.spiked)
        left,right=next(teeth(platform));x=(left+right)/2
        g.hero=Hero(x,platform.y+platform.h+SPIKE_DEPTH+54+8)
        g.hero.vy=-600;g.hero.face=face
        for _ in range(10):
            g.update(STEP,0,False,False)
            if g.hero_death.active:break
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'blade')
        return platform

    def test_real_blades_on_both_levels_fall_without_inputs_and_take_one_life(self):
        g=self.g
        for level in (1,4):
            for face in (-1,1):
                self.collide(level,face=face)
                g.time=.1  # Invisible phase of the respawn grace-period blink.
                with patch.object(g.blade_death_sprites,'draw',wraps=g.blade_death_sprites.draw) as draw:
                    g.draw(.5,present=False);draw.assert_called_once()
                x,y=g.hero.x,g.hero.y;self.assertEqual(g.hero_death.duration,1.2)
                for _ in range(75):g.update(STEP,1,True,True,fire=True,drop=True)
                self.assertEqual(g.hero.x,x);self.assertGreater(g.hero.y,y)
                self.assertFalse(g.hero.floating);self.assertFalse(g.solar.active)
                finish_respawn(g)
                self.assertEqual((g.lives,g.deaths,g.state),(2,1,'play'));self.assertEqual(g.energy.value,60)

    def test_pause_and_save_resume_the_cut_and_last_life_then_game_over(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble:
            self.collide(level=4,lives=1)
            rumble.assert_called_once_with('death',duration=1200)
            for _ in range(30):g.update(STEP,0,False,False)
            g.enter_menu('pause');data=capture(g)
            for _ in range(10):g.update(STEP,1,True,True)
            self.assertEqual(capture(g),data)
            restore(g,data);self.assertEqual(capture(g),data)
            g.resume_from_menu();rumble.assert_called_with('death',duration=950)
            bad=copy.deepcopy(data);bad['hero_death']['index']=1
            with self.assertRaises(ValueError):validate(bad)
            finish_respawn(g)
            self.assertEqual((g.lives,g.deaths,g.state),(0,1,'game_over'))
            self.assertFalse(g.resurrection.active)
            g.time=.1
            with patch.object(g.blade_death_sprites,'draw',wraps=g.blade_death_sprites.draw) as draw:
                g.draw(1,present=False);draw.assert_called_once()

    def test_all_preloaded_poses_draw_without_loading_or_transforming(self):
        g=self.g;self.collide()
        with patch('pygame.image.load',side_effect=AssertionError('runtime load')),\
             patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scale')),\
             patch('pygame.transform.flip',side_effect=AssertionError('runtime mirror')):
            for face in (-1,1):
                g.hero_death.hero_face=face
                for i in range(65):
                    g.hero_death.elapsed=i/64*1.2;g.hero_death.previous_elapsed=max(0,g.hero_death.elapsed-STEP)
                    before=capture(g);g.draw(.5,present=False);self.assertEqual(capture(g),before)

    def test_later_environmental_death_does_not_reuse_blade_clip(self):
        g=self.g;self.collide();finish_respawn(g)
        g.hero.y=900;g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'pit')
