import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import unittest
from unittest.mock import patch
import pygame as pg
from main import Game,Hero,STEP,EXIT_MARGIN
from medallion import position
from savegame import capture,restore,validate
from support import finish_respawn
from localization import CODES,translate


class ScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        self.g.new_game();self.g.state='play';self.g.invuln=100

    def test_collectibles_award_once_even_at_full_energy(self):
        g=self.g;g.energy.value=100
        x,y=g.gems[0];g.hero=Hero(x,y+28)
        g.update(STEP,0,False,False)
        self.assertEqual((g.score,g.level_score),(10,10))
        g.update(STEP,0,False,False);self.assertEqual(g.score,10)
        x,y=position(g.elapsed,g.medallion_anchor);g.hero=Hero(x,y+28)
        g.update(STEP,0,False,False)
        self.assertEqual((g.score,g.level_score),(510,510))
        g.update(STEP,0,False,False);self.assertEqual(g.score,510)

    def test_all_ray_targets_award_exactly_once(self):
        g=self.g
        for level in (1,2,3,4):
            with self.subTest(level=level):
                g.new_game();g.start_level(level);g.solar.elapsed=.2;g.solar.powered=True
                expected=(len(g.beetle_motions)*100+len(g.vultures)*200+
                          len(g.crocodiles)*100+len(g.scorpions)*300+len(g.gyrospheres)*200+len(g.vases)*10)
                with patch.object(g.solar,'bounds',return_value=pg.Rect(-1000,-1000,100000,100000)):
                    g.solar_hits();self.assertEqual((g.score,g.level_score),(expected,expected))
                    g.solar_hits();self.assertEqual(g.score,expected)
                g.solar.powered=False;g.solar_hits();self.assertEqual(g.score,expected)

    def test_completion_bonus_and_level_transition_do_not_duplicate_points(self):
        g=self.g
        for level in range(1,9):
            for lives in (1,3,4):
                g.new_game();g.start_level(level);g.lives=lives;g.award_points(50)
                expected=50+level*1000+lives*100
                g.complete_level();g.complete_level();g.draw_victory()
                self.assertEqual((g.score,g.level_score),(expected,expected))
                g.update(STEP,0,False,False);self.assertEqual(g.score,expected)
                g.continue_or_restart()
                self.assertEqual(g.level_score,0)
                self.assertEqual(g.score,expected if level<8 else 0)
                self.assertFalse(g.level_bonus_awarded)

    def test_real_level_end_triggers_bonus(self):
        g=self.g;g.hero=Hero(g.world_length+EXIT_MARGIN,620);g.hero.grounded=True
        g.update(STEP,0,False,False)
        self.assertEqual(g.state,'win');self.assertEqual(g.score,1300)

    def test_desert_temple_and_tower_completion_paths_award_their_bonus(self):
        g=self.g
        for level in (2,3,4):
            g.new_game();g.start_level(level);g.state='play';g.invuln=100
            if level==3:
                g.temple_exit.begin(g.hero)
                with patch.object(g.temple_exit,'update',return_value=True):g.update(STEP,0,False,False)
            else:
                path='desert_level.temple_entered' if level==2 else 'tower_level.completed'
                with patch(path,return_value=True):g.update(STEP,0,False,False)
            self.assertEqual(g.state,'win');self.assertTrue(g.level_bonus_awarded)
            self.assertGreaterEqual(g.score,level*1000+300)

    def test_death_save_and_restart_preserve_total_new_game_clears_it(self):
        g=self.g;g.award_points(810);g.kill_hero();finish_respawn(g)
        self.assertEqual((g.score,g.level_score),(810,810))
        data=capture(g);g.new_game();restore(g,data)
        self.assertEqual((g.score,g.level_score),(810,810))
        g.restart_level();self.assertEqual((g.score,g.level_score),(810,0))
        g.new_game();self.assertEqual((g.score,g.level_score),(0,0))

    def test_legacy_saves_start_at_zero_and_invalid_scores_are_rejected(self):
        g=self.g;g.award_points(510);data=capture(g)
        legacy=copy.deepcopy(data)
        for key in ('score','level_score','level_bonus_awarded'):del legacy[key]
        restore(g,legacy);self.assertEqual((g.score,g.level_score),(0,0))
        for key,value in (('score',-1),('score',True),('score',1.5),('score',float('nan')),
                          ('level_score',511),('level_bonus_awarded',1)):
            bad=copy.deepcopy(data);bad[key]=value
            with self.assertRaises(ValueError):validate(bad)
        del data['score']
        with self.assertRaises(ValueError):validate(data)

    def test_hud_and_both_summaries_show_total_without_changing_it(self):
        g=self.g;g.award_points(12340)
        for draw in (g.hud,g.draw_victory,g.draw_game_over):
            with patch.object(g,'text',wraps=g.text) as text:draw()
            labels=[call.args[0] for call in text.call_args_list]
            if draw==g.hud:
                self.assertIn('SCORE  ',labels)
                for digit in '12340':self.assertIn(digit,labels)
            elif draw==g.draw_victory:
                self.assertIn('Score total : 12 340',labels)
                self.assertIn('Points du niveau : 12 340',labels)
            else:self.assertTrue(any('SCORE  12 340' in label for label in labels))
            self.assertEqual(g.score,12340)

    def test_score_label_is_localized_without_changing_digits(self):
        for language in CODES:
            label=translate('SCORE  12 340   (+1 300)',language)
            self.assertIn('12 340   (+1 300)',label)
            for source in ('Score total : 12 340','Points du niveau : 1 300'):
                translated=translate(source,language)
                self.assertTrue(translated.endswith(source.split(' : ')[1]))
                if language!='fr':self.assertNotEqual(translated,source)
