import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch,MagicMock
from main import Game,Hero,STEP,WORLD
from medallion import MedallionInventory,POSITION,CORE_SIZE,CAPACITY,position,touches,tune,NOTES
from crystal import CORE_HEIGHT


class InventoryTests(unittest.TestCase):
    def test_once_per_level_capacity_and_future_extra_life(self):
        inventory=MedallionInventory()
        for level_id in (1,2,3):
            self.assertTrue(inventory.collect(level_id))
            self.assertFalse(inventory.collect(level_id))
        self.assertEqual(inventory.count,3);self.assertTrue(inventory.extra_life_ready)
        self.assertFalse(inventory.collect(4));self.assertEqual(inventory.count,CAPACITY)

    def test_double_size_near_two_thirds_and_four_note_melody(self):
        self.assertEqual(CORE_SIZE,CORE_HEIGHT*2)
        self.assertLess(abs(POSITION[0]-WORLD*2/3),200)
        self.assertEqual(len(NOTES),4)
        mono=tune(22050,1);stereo=tune(22050,2)
        self.assertEqual(len(stereo),2*len(mono));self.assertGreater(max(mono),1000)
        self.assertEqual(stereo[::2],mono);self.assertEqual(stereo[1::2],mono)


class MedallionGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        self.g.new_game();self.g.state='play';self.g.invuln=100

    def jump_to_reward(self):
        g=self.g;g.hero=Hero(POSITION[0],455);g.hero.grounded=True
        tick_of_pickup=None
        for tick in range(130):
            g.update(STEP,0,False,tick==0)
            if 1 in g.medallions.claimed_levels:
                tick_of_pickup=tick;break
        return tick_of_pickup

    def test_reward_is_reachable_only_near_top_of_actual_jump(self):
        self.assertFalse(touches(Hero(POSITION[0],455),0))
        tick=self.jump_to_reward()
        self.assertIsNotNone(tick)
        self.assertTrue(35<tick<75,tick)
        self.assertEqual(self.g.medallions.count,1)
        self.assertEqual(self.g.energy.value,60)
        self.assertEqual(len(self.g.gems),52)

    def test_medallion_and_inventory_survive_death_and_level_restart(self):
        self.jump_to_reward();g=self.g
        g.hero.y=900;g.update(STEP,0,False,False)
        self.assertEqual(g.medallions.count,1);self.assertFalse(g.medallions.available())
        g.reset();self.assertEqual(g.medallions.count,1)
        g.hero=Hero(POSITION[0],POSITION[1]+20)
        g.update(STEP,0,False,False)
        self.assertEqual(g.medallions.count,1)

    def test_third_distinct_medallion_grants_one_life_and_consumes_three(self):
        g=self.g;g.medallions.collect(2);g.medallions.collect(3)
        self.jump_to_reward()
        self.assertEqual(g.medallions.count,0);self.assertFalse(g.medallions.extra_life_ready)
        self.assertEqual(g.lives,4);self.assertGreater(g.extra_life_notice,0)
        for _ in range(5):g.update(STEP,0,False,False)
        self.assertEqual(g.lives,4);self.assertFalse(g.medallions.available())

    def test_obtaining_plays_jingle_once_and_honors_mute(self):
        g=self.g;old=g.sounds.get('medallion')
        try:
            for enabled in (True,False):
                g.medallions=MedallionInventory();g.reset();g.invuln=100;g.sound_on=enabled
                sample=MagicMock();g.sounds['medallion']=sample
                self.jump_to_reward()
                for _ in range(5):g.update(STEP,0,False,False)
                self.assertEqual(sample.play.call_count,1 if enabled else 0)
        finally:
            if old is not None:g.sounds['medallion']=old
            g.sound_on=True

    def test_hud_counts_are_prepared_and_drawing_is_read_only(self):
        g=self.g;g.cam=g.prev_cam=6000
        for count in range(4):self.assertIn((f'{count} / 3',20,(237,194,105),False),g.text_cache)
        before=(g.medallions.count,set(g.medallions.claimed_levels),g.elapsed)
        with patch.object(g.medallion_sprites,'draw',wraps=g.medallion_sprites.draw) as draw:
            g.draw(.5,present=False)
            self.assertEqual(draw.call_count,2)
        self.assertEqual(before,(g.medallions.count,set(g.medallions.claimed_levels),g.elapsed))


if __name__=='__main__':unittest.main()
