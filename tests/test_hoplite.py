import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import json
import unittest
from main import Game,Hero,Platform,ROOT,STEP
from hoplite import Hoplite,HopliteSprites,WALK_SPEED,RUN_SPEED,TURN_TIME,DEATH_TIME
from savegame import capture,restore,validate
from greece_levels import LEVELS


class HopliteBehaviorTests(unittest.TestCase):
    def guard(self,**kwargs):return Hoplite(500,300,700,0,1800,initial_facing=kwargs.get('facing',1))

    def test_slow_patrol_and_stationary_half_turn_stay_inside_limits(self):
        guard=self.guard();target=Hero(-2000,620)
        for _ in range(120):guard.update(STEP,target)
        self.assertAlmostEqual(guard.x,500+WALK_SPEED)
        guard.x=guard.px=700;guard.update(STEP,target)
        self.assertEqual(guard.state,'turn')
        for _ in range(20):guard.update(STEP,target)
        self.assertEqual((guard.x,guard.facing),(700,1))
        for _ in range(12):guard.update(STEP,target)
        self.assertEqual(guard.facing,-1)
        for _ in range(6000):
            guard.update(STEP,target)
            self.assertTrue(300<=guard.x<=700)

    def test_only_visible_target_in_front_starts_a_fast_pursuit(self):
        guard=self.guard();behind=Hero(200,620)
        guard.update(STEP,behind);self.assertEqual(guard.state,'patrol')
        target=Hero(1000,620);guard.update(STEP,target)
        self.assertEqual(guard.state,'alert')
        for _ in range(28):guard.update(STEP,target)
        self.assertEqual(guard.state,'chase')
        before=guard.x;guard.update(STEP,target)
        self.assertAlmostEqual(guard.x-before,RUN_SPEED*STEP)
        self.assertGreater(RUN_SPEED,340)

    def test_wall_and_high_platform_hide_target(self):
        guard=self.guard();target=Hero(1000,620)
        wall=Platform(700,400,80,220,True)
        self.assertFalse(guard.sees(target,[wall]))
        guard.update(STEP,target,[wall]);self.assertEqual(guard.state,'patrol')
        self.assertFalse(guard.sees(Hero(800,350)))
        self.assertFalse(guard.sees(Hero(2000,620)))

    def test_cannot_attack_during_respawn_protection_and_loses_hidden_target(self):
        guard=self.guard();target=Hero(1000,620)
        guard.update(STEP,target,can_attack=False);self.assertEqual(guard.state,'patrol')
        guard.state='chase'
        for _ in range(100):guard.update(STEP,Hero(1000,200))
        self.assertNotEqual(guard.state,'chase')

    def test_fast_guard_stops_at_pit_and_walls(self):
        guard=Hoplite(500,300,700,0,1200,initial_facing=1);guard.state='chase'
        for _ in range(400):
            guard.update(STEP,Hero(1300,620))
            self.assertLessEqual(guard.x,1168)
        guard=self.guard();guard.state='chase';wall=Platform(760,400,100,220,True)
        for _ in range(120):
            guard.update(STEP,Hero(1000,620),[wall]);self.assertLessEqual(guard.x,738)

    def test_body_contact_is_swept_and_a_jump_clears_the_skeleton(self):
        guard=self.guard();h=Hero(800,620);h.px=200
        self.assertTrue(guard.hits(h))
        h=Hero(500,490);self.assertFalse(guard.hits(h))
        guard.state='attack';guard.timer=.2
        self.assertTrue(guard.hits(Hero(590,620)))
        guard.ignite();self.assertFalse(guard.hits(Hero(500,620)))

    def test_death_finishes_once_and_stays_inert(self):
        guard=self.guard();self.assertTrue(guard.ignite());self.assertFalse(guard.ignite())
        for _ in range(240):guard.update(STEP,Hero(550,620))
        self.assertEqual((guard.x,guard.state,guard.death_timer),(500,'dead',DEATH_TIME))


class HopliteIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def setUp(self):self.g.new_game();self.g.sound_on=False

    def test_only_greek_levels_have_hoplites_on_real_floor_segments(self):
        g=self.g
        for level_id in range(1,9):
            g.start_level(level_id)
            self.assertEqual(len(g.hoplites),len(LEVELS[level_id].HOPLITES) if level_id>=5 else 0)
            for e in g.hoplites:
                self.assertTrue(any(p.ground and p.kind!='greek_ceiling' and p.y==e.y
                                    and p.x<=e.floor_left and p.x+p.w>=e.floor_right for p in g.platforms))
            if level_id>=5:self.assertEqual(g.crocodiles,[])

    def test_solar_kill_scores_once_and_bones_survive_death_and_save_reload(self):
        g=self.g;g.start_level(5);g.state='play';enemy=g.hoplites[0]
        g.hero=Hero(enemy.x-140,enemy.y);g.hero.face=1;g.energy.value=100
        for tick in range(30):g.update(STEP,0,False,False,fire=tick==0)
        self.assertFalse(enemy.alive);self.assertGreaterEqual(g.score,100)
        score=g.score
        for _ in range(40):g.update(STEP,0,False,False)
        self.assertEqual(g.score,score)
        expected=json.loads(json.dumps(capture(g)));restore(g,expected)
        self.assertEqual(json.loads(json.dumps(capture(g))),expected)
        g.respawn_hero();self.assertFalse(g.hoplites[0].alive)
        self.assertEqual(g.hoplites[0].death_timer,DEATH_TIME)

    def test_old_save_migration_and_chasing_guard_resume(self):
        g=self.g;g.start_level(7);g.state='play'
        enemy=g.hoplites[0];enemy.state='chase';enemy.x+=30
        expected=json.loads(json.dumps(capture(g)));restore(g,expected)
        self.assertEqual(json.loads(json.dumps(capture(g))),expected)
        old=copy.deepcopy(expected);del old['hoplites']
        restore(g,old);self.assertTrue(all(e.state=='patrol' for e in g.hoplites))
        self.assertEqual(g.taken,set(expected['taken']))
        corrupt=capture(g);corrupt['hoplites'][0]['x']=99999
        with self.assertRaises(ValueError):validate(corrupt)

    def test_contact_uses_sword_death_and_pause_freezes_guard(self):
        g=self.g;g.start_level(5);g.state='play';enemy=g.hoplites[0]
        g.hero=Hero(enemy.x,enemy.y);g.hero.grounded=True;g.invuln=0
        g.update(STEP,0,False,False)
        self.assertEqual((g.lives,g.hero_death.kind),(2,'sword'))
        before=copy.deepcopy(vars(enemy));g.state='pause';g.update(STEP,0,False,False)
        self.assertEqual(vars(enemy),before)

    def test_old_slot_at_a_new_guard_spawn_has_normal_reappearance_grace(self):
        g=self.g;g.start_level(5);enemy=g.hoplites[0]
        g.hero=Hero(enemy.spawn_x,enemy.y);g.hero.grounded=True;g.invuln=0
        old=capture(g);del old['hoplites'];restore(g,old)
        self.assertEqual(g.invuln,2.)
        broken=copy.deepcopy(old);broken['invuln']=-1
        with self.assertRaises(ValueError):validate(broken)
        g.state='play';g.update(STEP,0,False,False)
        self.assertEqual(g.deaths,0)

    def test_all_frames_use_one_atlas_and_sampling_has_no_state_side_effects(self):
        bank=self.g.hoplite_sprites
        self.assertEqual({key:len(value) for key,value in bank.clips.items()},
                         {'walk':16,'run':16,'turn':8,'attack':8,'death':12})
        self.assertEqual(len(bank.images),1)
        settled=bank.clips['death'][-1]
        self.assertLessEqual(abs(settled.atlas.subsurface(settled.areas[0]).get_bounding_rect(min_alpha=64).bottom-settled.pivot[1]),1)
        e=Hoplite(500,300,700,0,1200)
        for state in ('patrol','chase','turn','alert','attack','return','dead'):
            e.state=state;e.alive=state!='dead';e.timer=.12;e.distance=30
            before=copy.deepcopy(vars(e))
            for alpha in (0,.5,1):bank.sample(e,alpha).draw(self.g.canvas,500,620,1)
            self.assertEqual(vars(e),before)


if __name__=='__main__':unittest.main()
