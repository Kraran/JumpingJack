import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from level_bonus import sample
from main import Game
from savegame import capture


class BonusTimingTests(unittest.TestCase):
    def test_count_is_time_based_monotonic_and_bounded(self):
        for lives in (0,1,3,4,99):
            for hz in (30,60,75,144,240):
                last=0
                for frame in range(hz*4+1):
                    view=sample(frame/hz,lives)
                    self.assertLessEqual(last,view.points);self.assertLessEqual(view.points,lives*100)
                    self.assertEqual(view.remaining+view.counted,lives)
                    self.assertGreaterEqual(view.remaining,0)
                    last=view.points
                self.assertEqual((view.points,view.remaining),(lives*100,0))
        self.assertFalse(sample(.49,3).flying)
        self.assertEqual(sample(.5+.55,3).counted,1)
        self.assertEqual(sample(.5+1.1,3).counted,2)


class BonusGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def test_all_levels_count_without_changing_real_lives_or_score(self):
        g=self.g
        for level in (1,2,3,4):
            g.new_game();g.start_level(level);g.time=10.;g.award_points(40);g.complete_level()
            before=capture(g);score=g.score
            for elapsed in (0,.6,.9,1.4,2.15,4):
                g.time=10+elapsed
                with patch.object(g,'text',wraps=g.text) as text:g.draw_victory()
                labels=[call.args[0] for call in text.call_args_list]
                self.assertIn(f'× 100    +{sample(elapsed,3).points}',labels)
                self.assertEqual(capture(g),before);self.assertEqual(g.lives,3)
            self.assertIn(f'Score total : {score:,}'.replace(',',' '),labels)
            self.assertIn(f'Points du niveau : {score:,}'.replace(',',' '),labels)

    def test_skipping_and_duplicate_completion_keep_the_full_bonus(self):
        g=self.g;g.new_game();g.time=5.;g.complete_level()
        g.time=6.;g.complete_level()
        self.assertEqual(g.victory_started,5.);self.assertEqual(g.score,1300)
        g.continue_or_restart()
        self.assertEqual((g.level_id,g.score,g.lives),(2,1300,3))
        self.assertIsNone(g.victory_started)
