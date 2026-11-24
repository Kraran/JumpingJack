import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from main import Game,STEP


class StartupPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.reset();self.g.state='play';self.g.time=0;self.g.invuln=100

    def test_offscreen_preparation_preserves_gameplay_and_does_not_present_or_readback(self):
        g=self.g
        before=(dict(g.hero.__dict__),g.cam,g.prev_cam,g.time,g.elapsed,g.rng.getstate(),
                g.state,list(g.particles),set(g.taken),g.last_present,list(g.frame_intervals),list(g.submission_times))
        with patch.object(g.native_canvas,'present',side_effect=AssertionError('screen swap')),patch.object(g.native_canvas,'capture',side_effect=AssertionError('GPU readback')):
            g.prepare_rendering()
        after=(dict(g.hero.__dict__),g.cam,g.prev_cam,g.time,g.elapsed,g.rng.getstate(),
               g.state,list(g.particles),set(g.taken),g.last_present,list(g.frame_intervals),list(g.submission_times))
        self.assertEqual(before,after)

    def test_first_five_seconds_need_no_new_fonts_texts_or_common_rasters(self):
        g=self.g;g.prepare_rendering()
        texts=set(g.text_cache);primitives=set(g.native_canvas.primitives)
        with patch('main.pg.font.SysFont',side_effect=AssertionError('lazy font in play')):
            for frame in range(300):
                for step in range(2):
                    g.time+=STEP
                    g.update(STEP,1,30<=frame<90,frame==30 and step==0,
                             fire=frame in (10,170) and step==0,down=110<=frame<145)
                g.draw(.5,present=False)
        self.assertEqual(set(g.text_cache),texts)
        self.assertEqual(set(g.native_canvas.primitives),primitives)

    def test_all_shard_counter_values_are_already_prepared(self):
        for count in range(len(self.g.gems)+1):
            key=(f'{count:02} / {len(self.g.gems)}',23,(237,194,105),False)
            self.assertIn(key,self.g.text_cache)


if __name__=='__main__':unittest.main()
