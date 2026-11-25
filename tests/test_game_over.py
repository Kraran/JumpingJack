import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import unittest
from unittest.mock import patch,Mock
from main import Game,STEP
from gamepad import RUMBLE_EFFECTS
from lives import game_over_tune
from localization import CODES,translate
from savegame import capture,restore,validate


class GameOverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.state='play'

    def test_final_death_plays_feedback_once_and_freezes_the_world(self):
        g=self.g;g.lives=1;g.hero.y=900
        with patch.object(g.gamepads,'rumble') as rumble,patch.object(g,'sound') as sound:
            g.update(STEP,0,False,False)
            self.assertEqual((g.state,g.lives,g.deaths),('game_over',0,1))
            rumble.assert_called_once_with('game_over');sound.assert_called_once_with('game_over')
            elapsed=g.elapsed
            for _ in range(120):g.update(STEP,1,True,True,fire=True)
            self.assertEqual(g.elapsed,elapsed)
            rumble.assert_called_once();sound.assert_called_once()
        self.assertGreater(RUMBLE_EFFECTS['game_over'][2],RUMBLE_EFFECTS['death'][2])

    def test_game_over_displays_the_whole_run_in_every_level(self):
        g=self.g
        for level_id in range(1,5):
            with self.subTest(level=level_id):
                g.start_level(level_id);g.state='game_over';g.lives=0
                g.run_totals=dict(shards=11,elapsed=60.,deaths=2)
                g.taken={0,1,2};g.elapsed=65.5;g.deaths=1
                with patch.object(g,'text',wraps=g.text) as text:
                    g.draw(.5,present=False)
                calls=text.call_args_list
                self.assertTrue(any(c.args[0]=='GAME OVER' and c.args[2]>=80 for c in calls))
                self.assertEqual(sum(c.args[0]=='14 éclats solaires   ·   02:05   ·   3 morts' for c in calls),1)

    def test_totals_survive_level_changes_restarts_and_saves_and_reset_for_a_new_game(self):
        g=self.g;g.taken={0,1};g.elapsed=60.;g.deaths=1;g.state='win'
        g.continue_or_restart()
        self.assertEqual(g.level_id,2)
        self.assertEqual(g.run_totals,dict(shards=2,elapsed=60.,deaths=1))
        g.taken={0};g.elapsed=15.;g.deaths=1;g.restart_level()
        expected=dict(shards=3,elapsed=75.,deaths=2)
        self.assertEqual(g.run_totals,expected)
        data=capture(g);g.new_game();restore(g,data)
        self.assertEqual(g.run_totals,expected)
        legacy=copy.deepcopy(data);del legacy['run_totals'];restore(g,legacy)
        self.assertEqual(g.run_totals,dict(shards=0,elapsed=0.,deaths=0))
        for key,value in (('shards',-1),('elapsed',float('nan')),('deaths',True)):
            bad=copy.deepcopy(data);bad['run_totals'][key]=value
            with self.assertRaises(ValueError):validate(bad)
        g.new_game();self.assertEqual(g.run_totals,dict(shards=0,elapsed=0.,deaths=0))

    def test_sound_generation_mute_and_translated_results(self):
        mono=game_over_tune(22050,1);stereo=game_over_tune(22050,2)
        self.assertEqual(len(stereo),len(mono)*2)
        self.assertGreater(len(mono),22050);self.assertGreater(max(mono),1000)
        self.assertLess(max(abs(v) for v in mono),32768)
        g=self.g
        with patch.dict(g.sounds,{'game_over':Mock()}):
            g.sound_on=False;g.sound('game_over');g.sounds['game_over'].play.assert_not_called()
            g.sound_on=True;g.sound('game_over');g.sounds['game_over'].play.assert_called_once()
        for language in CODES:
            result=translate('14 éclats solaires   ·   02:05   ·   3 morts',language)
            for value in ('14','02:05','3'):self.assertIn(value,result)
            if language!='fr':self.assertNotIn('éclats solaires',result)
