import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock,patch
from main import Game,Hero,STEP
from crystal import FRAMES,PERIOD


class CrystalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.reset();self.g.state='play';self.g.invuln=100

    def test_complete_loop_uses_48_poses_and_shards_have_different_phases(self):
        sprites=self.g.crystal_sprites
        self.assertEqual({sprites.sample((i+.2)*PERIOD/FRAMES) for i in range(FRAMES)},set(range(FRAMES)))
        self.assertEqual(sprites.sample(0),sprites.sample(PERIOD))
        self.assertEqual(len({sprites.sample(0,index) for index in range(8)}),8)
        self.assertEqual(len(sprites.images),1)

    def test_rendering_needs_no_load_transform_or_new_raster(self):
        sprites=self.g.crystal_sprites;canvas=MagicMock();canvas.point.return_value=(100,100)
        with patch('pygame.image.load',side_effect=AssertionError('runtime load')),patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scale')):
            for i in range(FRAMES):sprites.draw(canvas,100,100,i*PERIOD/FRAMES)
        self.assertEqual(canvas.native.blit.call_count,FRAMES)
        self.assertTrue(all(call.args[0] is sprites.atlas for call in canvas.native.blit.call_args_list))

    def test_game_uses_interpolated_simulation_time_instead_of_wall_clock(self):
        g=self.g;g.previous_elapsed=1;g.elapsed=2;g.time=999
        with patch.object(g.crystal_sprites,'draw') as draw:g.draw(.25,present=False)
        self.assertGreater(draw.call_count,1)
        self.assertTrue(all(call.args[3]==1.25 for call in draw.call_args_list))
        g.state='pause';before=g.elapsed
        with patch.object(g,'close'),patch('main.pg.event.get',return_value=[]):g.run(frames=2)
        self.assertEqual(g.elapsed,before)

    def test_collection_still_recharges_ten_once_and_removes_the_crystal(self):
        g=self.g;x,y=g.gems[0];g.hero=Hero(x,y+28);g.energy.value=30
        for _ in range(2):g.update(STEP,0,False,False)
        self.assertEqual(g.energy.value,40);self.assertIn(0,g.taken)
        with patch.object(g.crystal_sprites,'draw') as draw:g.draw(1,present=False)
        self.assertFalse(any(len(call.args)>4 and call.args[4]==0 for call in draw.call_args_list))
        self.assertEqual(len(g.gems),52)
