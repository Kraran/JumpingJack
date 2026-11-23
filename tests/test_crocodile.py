import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
from types import SimpleNamespace
import unittest
import pygame as pg
from crocodile import (Crocodile, CrocodileSprites, create_crocodiles, segment_box,
                       WALK_SPEED, LUNGE_SPEED, WARNING, RECOVERY, TURN_TIME)
from main import Game, Hero, ROOT, STEP, level


def hero(x,y=620):return SimpleNamespace(x=x,px=x,y=y,py=y)


class CrocodileBehaviorTests(unittest.TestCase):
    def enemy(self):return Crocodile(500,300,700,0,1200)

    def test_slow_patrol_stays_on_its_ground(self):
        enemy=self.enemy();far=hero(-1000)
        for _ in range(120):enemy.update(STEP,far)
        self.assertAlmostEqual(enemy.x,500-WALK_SPEED)
        for _ in range(120*30):
            enemy.update(STEP,far)
            self.assertGreaterEqual(enemy.x,300);self.assertLessEqual(enemy.x,700)
            self.assertEqual(enemy.y,620)

    def test_close_target_triggers_warning_then_fast_charge(self):
        enemy=self.enemy();target=hero(680)
        enemy.facing=1
        self.assertEqual(enemy.update(STEP,target),'warning')
        self.assertEqual(enemy.facing,1)
        self.assertEqual(enemy.x,500)
        for _ in range(30):
            enemy.update(STEP,target)
            if enemy.state=='lunge':break
        self.assertEqual(enemy.state,'lunge')
        previous=enemy.x;enemy.update(STEP,target)
        self.assertAlmostEqual(enemy.x-previous,LUNGE_SPEED*STEP)
        self.assertGreater(LUNGE_SPEED,3*340)

    def test_jumping_high_does_not_trigger_a_ground_attack(self):
        enemy=self.enemy();enemy.update(STEP,hero(600,450))
        self.assertEqual(enemy.state,'patrol')

    def test_charge_commits_to_its_initial_direction(self):
        enemy=self.enemy();target=hero(680)
        enemy.update(STEP,target)
        target.x=300
        for _ in range(50):enemy.update(STEP,target)
        self.assertEqual(enemy.facing,1)
        self.assertGreater(enemy.x,500)

    def test_charge_stops_at_pit_and_recovers(self):
        enemy=Crocodile(1050,850,1100,0,1220,initial_facing=1)
        enemy.state='lunge';target=hero(1400)
        for _ in range(40):
            enemy.update(STEP,target)
            self.assertLessEqual(enemy.x,1220-108)
        self.assertEqual(enemy.state,'recover')
        for _ in range(180):enemy.update(STEP,hero(-1000))
        self.assertEqual(enemy.state,'patrol')

    def test_boundary_turn_is_stationary_and_commits_direction_at_end(self):
        enemy=Crocodile(300,300,700,0,1200)
        enemy.update(STEP,hero(-1000))
        self.assertEqual((enemy.state,enemy.facing),('turn',-1))
        x=enemy.x
        for _ in range(10):
            enemy.update(STEP,hero(-1000))
            self.assertEqual(enemy.x,x)
            self.assertEqual(enemy.facing,-1)
        for _ in range(10):enemy.update(STEP,hero(-1000))
        self.assertEqual((enemy.state,enemy.facing),('patrol',1))

    def test_target_behind_causes_turn_before_warning(self):
        enemy=self.enemy();target=hero(680)
        self.assertIsNone(enemy.update(STEP,target))
        self.assertEqual((enemy.state,enemy.facing,enemy.turn_to),('turn',-1,1))
        event=None
        for _ in range(20):event=enemy.update(STEP,target) or event
        self.assertEqual((enemy.state,enemy.facing,event),('warning',1,'warning'))
        self.assertEqual(enemy.x,500)

    def test_target_jumping_away_cancels_attack_after_turn(self):
        enemy=self.enemy();enemy.update(STEP,hero(680))
        for _ in range(20):enemy.update(STEP,hero(680,400))
        self.assertEqual((enemy.state,enemy.facing),('patrol',1))

    def test_mid_turn_does_not_keep_a_phantom_sideways_snout(self):
        enemy=self.enemy();enemy.facing=1;enemy.start_turn(-1)
        enemy.timer=TURN_TIME/2
        self.assertFalse(enemy.hits(hero(590)))
        self.assertTrue(enemy.hits(hero(540)))

    def test_swept_collision_catches_lunge_that_crosses_player(self):
        enemy=self.enemy();enemy.facing=1
        enemy.px=500;enemy.x=710;enemy.state=enemy.previous_state='lunge'
        self.assertTrue(enemy.hits(hero(620)))
        self.assertFalse(enemy.hits(hero(620,540)))

    def test_fast_player_cannot_tunnel_through_body(self):
        enemy=self.enemy();target=hero(900);target.px=200
        self.assertTrue(enemy.hits(target))

    def test_jump_clearance_uses_the_full_relative_trajectory(self):
        enemy=self.enemy();enemy.facing=1
        target=hero(650,480);target.px=300;target.py=620
        self.assertFalse(enemy.hits(target))
        target.y=580
        self.assertTrue(enemy.hits(target))

    def test_stationary_segment_inside_and_outside(self):
        self.assertTrue(segment_box((5,5),(0,0),(0,0,10,10)))
        self.assertFalse(segment_box((11,5),(0,0),(0,0,10,10)))

    def test_reset_restores_patrol_and_spawn(self):
        enemy=self.enemy();enemy.x=660;enemy.state='lunge';enemy.timer=.2
        enemy.reset()
        self.assertEqual((enemy.x,enemy.px,enemy.state,enemy.timer),(500,500,'patrol',0))


class CrocodileIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.game=Game(True)
    @classmethod
    def tearDownClass(cls):cls.game.close()
    def setUp(self):self.game.reset();self.game.state='play'

    def test_body_contact_kills_and_resets_enemy(self):
        enemy=self.game.crocodiles[0]
        self.game.hero=Hero(enemy.x,620)
        self.game.update(STEP,0,False,False)
        self.assertEqual(self.game.deaths,1)
        self.assertEqual(self.game.hero.x,160)
        self.assertGreater(self.game.invuln,0)
        self.assertEqual(enemy.state,'patrol')

    def test_respawn_protection_prevents_contact_death_and_new_attack(self):
        enemy=self.game.crocodiles[0]
        self.game.hero=Hero(enemy.x,620);self.game.invuln=2
        self.game.update(STEP,0,False,False)
        self.assertEqual(self.game.deaths,0)
        self.assertEqual(enemy.state,'patrol')

    def test_all_placements_have_a_real_continuous_floor(self):
        floors=[p for p in level()[0] if p.ground]
        self.assertEqual(len(self.game.crocodiles),3)
        for enemy in self.game.crocodiles:
            self.assertTrue(any(p.x==enemy.floor_left and p.x+p.w==enemy.floor_right and p.y==enemy.y for p in floors))
            self.assertGreaterEqual(enemy.patrol_left,enemy.floor_left+108)
            self.assertLessEqual(enemy.patrol_right,enemy.floor_right-108)

    def test_32_poses_and_both_directions_are_loaded(self):
        sprites=self.game.crocodile_sprites
        self.assertIsNotNone(sprites)
        self.assertEqual((len(sprites.walk),len(sprites.attack),len(sprites.turn),len(sprites.images)),(16,8,8,64))
        for image in sprites.images:
            self.assertEqual(image.get_size(),(384,128))
            self.assertGreater(image.get_bounding_rect(min_alpha=32).width,30)

    def test_render_patrol_warning_lunge_and_recovery(self):
        enemy=self.game.crocodiles[0]
        self.game.cam=self.game.prev_cam=400
        for state in ('patrol','turn','warning','lunge','recover'):
            enemy.state=enemy.previous_state=state
            enemy.timer=.05
            self.game.draw(.5)


if __name__=='__main__':unittest.main()
