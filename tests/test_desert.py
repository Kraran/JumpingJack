import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP,WORLD,EXIT_MARGIN,VIEW_W,level
from gamepad import PadSnapshot
from beetle import BeetleMotion
import desert_level as desert
from terrain import sand_height


class DesertGeometryTests(unittest.TestCase):
    def test_length_five_footbridges_five_solid_rocks_and_enemy_zones(self):
        self.assertEqual(desert.LENGTH,WORLD*1.5)
        platforms,gems=level(2)
        self.assertEqual(sum(p.kind=='bridge' for p in platforms),5)
        self.assertEqual(sum(p.kind=='rock' and p.ground for p in platforms),5)
        self.assertFalse(any(p.x==13700 and p.kind=='rock' for p in platforms))
        self.assertFalse(any(p.x==14100 and not p.ground for p in platforms))
        self.assertEqual(len(gems),73)
        for spawn in desert.CROCODILES:self.assertLess(spawn[4],3800)
        for spawns in (desert.BEETLES,desert.VULTURES):
            self.assertTrue(any(x<desert.RIVER[1] for x,y in spawns))
            self.assertTrue(any(x>desert.RIVER[1] for x,y in spawns))
        self.assertEqual(desert.MEDALLION[0]/desert.LENGTH,.9)
        self.assertEqual(len(desert.CHECKPOINTS),2)

    def test_rocks_block_walking_and_cannot_be_dropped_through(self):
        platforms,_=level(2)
        for rock in (p for p in platforms if p.kind=='rock'):
            hero=Hero(rock.x-60,sand_height(rock.x-60));hero.grounded=True
            for _ in range(90):hero.update(STEP,1,False,False,platforms)
            self.assertLessEqual(hero.x,rock.x-15);self.assertEqual(hero.vx,0)
            hero=Hero(rock.x+rock.w/2,rock.y);hero.grounded=True
            hero.update(STEP,0,True,True,platforms,drop=True)
            self.assertEqual(hero.y,rock.y);self.assertIsNone(hero.ignored_platform)

    def test_normal_jump_or_glide_cannot_cross_the_river_without_footbridges(self):
        platforms,_=level(2);platforms=[p for p in platforms if p.kind!='bridge']
        for glide in (False,True):
            hero=Hero(desert.RIVER[0]-18,620);hero.grounded=True;hero.vx=340
            for tick in range(1200):
                hero.update(STEP,1,glide,tick==0,platforms)
                if desert.water_hits(hero):break
            self.assertTrue(desert.water_hits(hero));self.assertLess(hero.x,desert.RIVER[1])

    def test_custom_scarab_spawn_indices_cover_the_longer_level(self):
        platforms,_=level(2)
        for index,home in enumerate(desert.BEETLES):
            enemy=BeetleMotion(index,spawns=desert.BEETLES)
            for tick in range(180):enemy.update(STEP,tick*STEP,None,platforms,can_attack=False)
            self.assertLess(abs(enemy.x-home[0]),106)
            self.assertLess(abs(enemy.y-home[1]),150)
            self.assertLess(enemy.y,sand_height(enemy.x))


class DesertGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        self.g.new_game();self.g.start_level(2);self.g.state='play';self.g.invuln=100

    def test_finishing_first_level_continues_to_second_with_lives_and_medallion(self):
        g=self.g;g.new_game();g.state='play';g.lives=2;g.medallions.collect(1)
        g.hero=Hero(WORLD+EXIT_MARGIN,620);g.hero.grounded=True
        g.update(STEP,0,False,False);self.assertEqual(g.state,'win')
        g.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True))
        self.assertEqual((g.level_id,g.state,g.world_length),(2,'play',14400))
        self.assertEqual((g.lives,g.medallions.count),(2,1))
        self.assertTrue(g.medallions.available(2));self.assertFalse(g.pending_jump)
        self.assertEqual((len(g.beetle_motions),len(g.vultures),len(g.crocodiles)),(10,6,3))

    def test_river_is_fatal_during_glide_even_with_respawn_protection(self):
        g=self.g
        for lives in (2,1,0):
            g.hero=Hero(1150,650);g.hero.vy=105;g.hero.floating=True;g.invuln=100
            with patch.object(g.gamepads,'rumble') as rumble:
                g.update(STEP,0,True,False);rumble.assert_called_once_with('death')
            self.assertEqual(g.lives,lives)
            if lives:self.assertEqual(g.hero.x,160)
        self.assertEqual(g.state,'game_over');g.draw(1,present=False)

    def test_footbridge_decks_are_safe_supports_above_the_water(self):
        g=self.g
        for bridge in (p for p in g.platforms if p.kind=='bridge'):
            g.hero=Hero(bridge.x+bridge.w/2,bridge.y);g.hero.grounded=True;g.invuln=100
            for _ in range(15):g.update(STEP,0,False,False)
            self.assertEqual(g.hero.y,bridge.y);self.assertTrue(g.hero.grounded)
            self.assertEqual(g.lives,3)

    def test_both_pylons_activate_and_latest_checkpoint_survives_death(self):
        g=self.g
        for index,x in enumerate(desert.CHECKPOINTS,1):
            y=sand_height(x)
            g.hero=Hero(x,y);g.hero.grounded=True;g.update(STEP,0,False,False)
            self.assertEqual(g.check_index,index);self.assertEqual(g.checkpoint,(x-60,y))
        g.hero.y=900;g.update(STEP,0,False,False)
        self.assertEqual((g.hero.x,g.hero.y),(9540,sand_height(9600)))
        self.assertTrue(all(pylon.active for pylon in g.obelisks))
        g.reset();self.assertEqual(g.level_id,2)
        self.assertTrue(all(not pylon.active for pylon in g.obelisks))

    def test_backtracking_to_an_older_pylon_does_not_move_respawn_backwards(self):
        g=self.g
        for x in reversed(desert.CHECKPOINTS):
            g.hero=Hero(x,sand_height(x));g.hero.grounded=True;g.update(STEP,0,False,False)
        self.assertEqual(g.checkpoint,(9540,sand_height(9600)));self.assertEqual(g.check_index,2)
        self.assertTrue(all(pylon.active for pylon in g.obelisks))

    def test_near_end_medallion_is_reachable_and_stays_taken_after_restart(self):
        g=self.g;g.medallions.collect(1)
        g.hero=Hero(desert.MEDALLION[0],455);g.hero.grounded=True
        tick=None
        for tick in range(130):
            g.update(STEP,0,False,tick==0)
            if 2 in g.medallions.claimed_levels:break
        self.assertTrue(35<tick<75,tick);self.assertEqual(g.medallions.count,2)
        g.handle_pad(PadSnapshot(back_pressed=True))
        self.assertEqual(g.level_id,2);self.assertEqual(g.medallions.count,2)
        self.assertFalse(g.medallions.available(2))

    def test_defeated_enemies_remain_dead_in_level_two_after_losing_a_life(self):
        g=self.g;g.dead_beetles.add(8);g.crocodiles[0].ignite();g.vultures[4].ignite()
        g.hero.y=900;g.update(STEP,0,False,False)
        self.assertEqual(g.lives,2);self.assertIn(8,g.dead_beetles)
        self.assertFalse(g.crocodiles[0].alive);self.assertFalse(g.vultures[4].alive)
        self.assertEqual(g.vultures[5].home,desert.VULTURES[5])
        self.assertEqual(g.beetle_motions[8].spawns,desert.BEETLES)

    def test_second_level_temple_exit_stays_fluid_and_continues_into_temple(self):
        g=self.g;g.hero=Hero(desert.LENGTH-80,620);g.hero.grounded=True;g.hero.vx=340
        g.cam=g.prev_cam=desert.LENGTH-VIEW_W
        for _ in range(120):
            before=g.hero.x;g.update(STEP,1,False,False)
            self.assertAlmostEqual(g.hero.x-before,340*STEP)
            self.assertEqual(g.hero.y,620);self.assertEqual(g.cam,desert.LENGTH-VIEW_W)
            if g.state=='win':break
        self.assertEqual(g.state,'win');g.draw(1,present=False)
        g.handle_pad(PadSnapshot(start_pressed=True))
        self.assertEqual((g.level_id,g.lives,g.state),(3,3,'play'))

    def test_temple_finishes_only_after_entering_at_doorway_height(self):
        g=self.g;g.hero=Hero(desert.TEMPLE_FINISH-5,620);g.hero.grounded=True
        g.update(STEP,0,False,False);self.assertEqual(g.state,'play')
        g.hero=Hero(desert.TEMPLE_FINISH+5,desert.TEMPLE_DOOR_TOP-30)
        g.update(STEP,0,False,False);self.assertEqual(g.state,'play')
        g.hero=Hero(desert.TEMPLE_FINISH+5,620);g.hero.grounded=True
        g.update(STEP,0,False,False);self.assertEqual(g.state,'win')

    def test_final_sand_approach_can_be_walked_into_the_temple(self):
        g=self.g;g.hero=Hero(13670,sand_height(13670));g.hero.grounded=True
        for _ in range(360):
            g.update(STEP,1,False,False)
            if g.state=='win':break
        self.assertEqual(g.state,'win');self.assertEqual(g.hero.y,620)
        self.assertEqual(g.lives,3);self.assertLess(g.hero.x,desert.LENGTH)

    def test_parallax_covers_end_of_level_and_render_needs_no_lazy_assets_or_texts(self):
        g=self.g;texts=set(g.text_cache)
        far=g.desert_art.layers[0]
        self.assertGreaterEqual(far.image.get_width()-far.offset((desert.LENGTH-VIEW_W)*1.5),1920)
        self.assertEqual([layer.numerator for layer in g.desert_art.layers],[2,6,12])
        with patch('pygame.image.load',side_effect=AssertionError('lazy image load')),\
             patch('main.pg.font.SysFont',side_effect=AssertionError('lazy font')):
            for camera in (0,1800,4100,9200,12500,13120):
                g.cam=g.prev_cam=camera;g.hero.x=camera+400
                g.draw(.5,present=False)
        self.assertEqual(texts,set(g.text_cache))


if __name__=='__main__':unittest.main()
