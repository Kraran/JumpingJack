import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from hero_death import DURATION,CAPTURE,FRAMES
from savegame import capture,restore,validate
from support import finish_respawn


class CrocodileDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.state='play'

    def collide(self,level=1,lives=3,side=1):
        g=self.g;g.start_level(level);g.lives=lives;g.state='play'
        enemy=g.crocodiles[0]
        g.hero=Hero(enemy.x+side*40,enemy.y);g.hero.grounded=True
        g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active)
        return enemy

    def finish(self):
        finish_respawn(self.g)

    def test_real_collision_runs_both_directions_then_respawns_once_in_both_levels(self):
        g=self.g
        for level in (1,2):
            for side in (-1,1):
                with self.subTest(level=level,side=side):
                    self.collide(level,side=side)
                    self.assertEqual((g.lives,g.deaths,g.state),(2,1,'play'))
                    self.assertEqual(g.hero_death.facing,side)
                    origin=(g.hero.x,g.hero.y);g.update(STEP,1,True,True,fire=True)
                    self.assertEqual((g.hero.x,g.hero.y),origin);self.assertFalse(g.solar.active)
                    self.finish()
                    self.assertFalse(g.hero_death.active);self.assertEqual((g.lives,g.deaths),(2,1))
                    self.assertEqual(g.hero.x,g.checkpoint[0]);self.assertGreater(g.invuln,0)
                    self.assertTrue(g.menu_gameplay_blocked)

    def test_last_life_waits_for_animation_before_game_over_and_preserves_feedback(self):
        g=self.g
        with patch.object(g,'sound') as sound,patch.object(g.gamepads,'rumble') as rumble:
            self.collide(lives=1)
            self.assertEqual((g.state,g.lives),('play',0))
            self.assertNotIn(('game_over',),[c.args for c in sound.call_args_list])
            self.finish()
            self.assertEqual(g.state,'game_over');self.assertEqual(g.deaths,1)
            self.assertEqual([c.args for c in rumble.call_args_list],[('death',),('game_over',)])
            self.assertEqual(rumble.call_args_list[0].kwargs,{'duration':1750})
            self.assertEqual(sum(c.args==('game_over',) for c in sound.call_args_list),1)

    def test_rumble_covers_the_clip_and_resumes_only_the_remaining_time_after_pause(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble,patch.object(g.gamepads,'stop_rumble') as stop:
            self.collide()
            rumble.assert_called_once_with('death',duration=1750)
            stop.reset_mock()
            for _ in range(48):g.update(STEP,0,False,False)
            g.enter_menu('pause');stop.assert_called_once_with()
            elapsed=g.hero_death.elapsed
            for _ in range(20):g.update(STEP,0,False,False)
            self.assertEqual(g.hero_death.elapsed,elapsed)
            g.resume_from_menu();rumble.assert_called_with('death',duration=1350)
            stop.reset_mock();self.finish();stop.assert_called_once_with()
            self.assertEqual(rumble.call_count,2)

    def test_pause_and_save_resume_even_after_the_last_life(self):
        g=self.g;self.collide(lives=1)
        for _ in range(50):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=json.loads(json.dumps(capture(g)))
        for _ in range(20):g.update(STEP,1,True,True)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)
        restore(g,data);self.assertEqual(json.loads(json.dumps(capture(g))),data)
        g.resume_from_menu();self.finish();self.assertEqual(g.state,'game_over')
        bad=data.copy();bad['hero_death']=dict(data['hero_death'],index=9)
        with self.assertRaises(ValueError):validate(bad)
        g.new_game();legacy=capture(g);del legacy['hero_death'];restore(g,legacy)
        self.assertFalse(g.hero_death.active)

    def test_all_poses_render_without_mutation_or_runtime_transforms(self):
        g=self.g;self.collide()
        with patch('pygame.transform.flip',side_effect=AssertionError('runtime flip')),\
             patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scaling')):
            for facing in (-1,1):
                g.hero_death.facing=facing
                for i in range(FRAMES+2):
                    t=(DURATION*i/(FRAMES+1))
                    g.hero_death.elapsed=t;g.hero_death.previous_elapsed=max(0,t-STEP)
                    before=json.loads(json.dumps(capture(g)))
                    g.draw(.5,present=False)
                    self.assertEqual(json.loads(json.dumps(capture(g))),before)
