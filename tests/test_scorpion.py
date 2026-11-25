import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import math
import unittest
from types import SimpleNamespace
import pygame as pg
from unittest.mock import patch
from main import Game,Hero,Platform,STEP
from scorpion import Scorpion,LaserBolt,CHARGE,TURN_TIME,TURN_FRAMES,BOLT_SPEED,SPAWNS,DEATH_TIME,DEATH_FRAMES,EXPLOSION_SIZE
from savegame import capture,restore,validate


class ScorpionPhysicsTests(unittest.TestCase):
    def enemy(self,face=1):return Scorpion(0,((400,300,500,620,face),))

    def test_all_front_angles_track_continuously_and_fire_a_lethal_bolt(self):
        for face in (-1,1):
            for angle in (0,15,30,45,60,75,90):
                enemy=self.enemy(face);x,y=enemy.pivot();a=math.radians(angle)
                hero=Hero(x+face*math.cos(a)*300,y-math.sin(a)*300+27)
                bolt=None;previous=enemy.angle
                for _ in range(120):
                    bolt=enemy.update(STEP,hero,[])
                    self.assertLessEqual(abs(enemy.angle-previous),240*STEP+1e-6);previous=enemy.angle
                    if bolt:break
                self.assertIsNotNone(bolt,(face,angle))
                self.assertAlmostEqual(enemy.angle,angle,delta=.01)
                self.assertAlmostEqual(math.hypot(bolt.vx,bolt.vy),BOLT_SPEED)
                self.assertLessEqual(bolt.vy,0);self.assertGreaterEqual(bolt.vx*face,-1e-8)

    def test_no_attack_behind_or_through_stone_and_no_instant_shot(self):
        enemy=self.enemy();hero=Hero(150,620)
        for _ in range(60):self.assertIsNone(enemy.update(STEP,hero,[]))
        enemy=self.enemy();hero=Hero(700,620);wall=Platform(550,300,32,400,True)
        for _ in range(60):self.assertIsNone(enemy.update(STEP,hero,[wall]))
        enemy=self.enemy()
        for _ in range(round(CHARGE/STEP)-2):self.assertIsNone(enemy.update(STEP,hero,[]))

    def test_patrol_turns_at_its_limits_without_leaving_the_floor(self):
        enemy=self.enemy();enemy.x=499;hero=Hero(1000,200)
        for _ in range(80):enemy.update(STEP,hero,[],can_attack=False)
        self.assertEqual(enemy.facing,-1);self.assertGreaterEqual(enemy.x,300);self.assertLessEqual(enemy.x,500)
        self.assertEqual(enemy.y,620)

    def test_body_contact_is_lethal_but_jumping_above_it_is_safe(self):
        enemy=self.enemy();self.assertTrue(enemy.hits(Hero(400,620)))
        self.assertFalse(enemy.hits(Hero(400,560)))
        hero=Hero(400,620);hero.px=100;hero.x=700
        self.assertTrue(enemy.hits(hero))

    def test_projectile_sweep_hits_a_stationary_and_a_crossing_hero(self):
        hero=Hero(200,620);bolt=LaserBolt(0,590,2000,0)
        self.assertTrue(bolt.update(.2,hero,[]));self.assertFalse(bolt.alive)
        hero=Hero(400,620);hero.px=0
        bolt=LaserBolt(400,590,-2000,0)
        self.assertTrue(bolt.update(.2,hero,[]))

    def test_stone_blocks_a_projectile_before_the_hero(self):
        hero=Hero(400,620);wall=Platform(200,400,20,240,True)
        bolt=LaserBolt(0,590,2000,0)
        self.assertFalse(bolt.update(.3,hero,[wall]));self.assertFalse(bolt.alive)
        self.assertLess(bolt.x,wall.x)

    def test_crouching_and_respawn_protection_avoid_the_horizontal_laser(self):
        hero=Hero(200,620);hero.crouch=hero.previous_crouch=1.
        self.assertFalse(LaserBolt(0,568,2000,0).update(.2,hero,[]))
        self.assertFalse(LaserBolt(0,590,2000,0).update(.2,Hero(200,620),[],can_hit=False))

    def test_dead_scorpion_stops_attacking_and_only_dies_once(self):
        enemy=self.enemy();self.assertTrue(enemy.ignite());self.assertFalse(enemy.ignite())
        for _ in range(150):self.assertIsNone(enemy.update(STEP,Hero(500,620),[]))
        self.assertFalse(enemy.hits(Hero(400,620)))

    def test_turn_keeps_support_position_and_cannot_fire_before_finishing(self):
        enemy=self.enemy();enemy.turn_to=-1;enemy.change('turn');x=enemy.x
        for _ in range(round(TURN_TIME/STEP)-1):
            self.assertIsNone(enemy.update(STEP,Hero(450,620),[]))
            self.assertEqual(enemy.x,x);self.assertEqual(enemy.facing,1)
        for _ in range(2):enemy.update(STEP,Hero(450,620),[])
        self.assertEqual(enemy.facing,-1);self.assertEqual(enemy.state,'patrol')


class ScorpionGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.start_level(3);self.g.state='play';self.g.invuln=100

    def test_five_spawn_only_in_temple_and_patrols_stay_on_safe_ground(self):
        g=self.g;self.assertEqual(len(g.scorpions),5)
        for enemy in g.scorpions:
            self.assertTrue(any(p.ground and p.kind=='temple_floor' and p.x<=enemy.left-90 and p.x+p.w>=enemy.right+90 for p in g.platforms))
        for level in (1,2):g.start_level(level);self.assertEqual(g.scorpions,[])

    def test_laser_death_costs_one_life_rumbles_and_clears_projectiles(self):
        g=self.g;g.hero=Hero(1000,620);g.hero.grounded=True;g.invuln=0
        g.laser_bolts=[LaserBolt(990,590,660,0),LaserBolt(990,590,660,0)]
        with patch.object(g.gamepads,'rumble') as rumble:g.update(STEP,0,False,False)
        self.assertEqual(g.lives,2);self.assertEqual(g.laser_bolts,[])
        self.assertEqual(sum(call.args==('death',) for call in rumble.call_args_list),1)

    def test_solar_ray_destroys_scorpion_and_dead_enemy_survives_life_loss(self):
        g=self.g;enemy=g.scorpions[0];g.hero=Hero(enemy.x-350,620);g.hero.face=1
        g.solar.elapsed=.2;g.solar.powered=True;g.solar.facing=1;g.solar.crouched=True
        g.solar_hits();self.assertFalse(enemy.alive)
        g.hero.y=900;g.update(STEP,0,False,False);self.assertFalse(g.scorpions[0].alive)
        self.assertEqual(g.lives,2)

    def test_pause_does_not_advance_enemy_or_projectile_and_drawing_needs_no_transforms(self):
        g=self.g;g.cam=g.prev_cam=850;g.laser_bolts=[LaserBolt(1600,500,-660,0)];g.state='pause'
        before=json.loads(json.dumps(capture(g)))
        with patch('pygame.transform.rotozoom',side_effect=AssertionError('runtime rotation')),\
             patch('pygame.image.load',side_effect=AssertionError('runtime image loading')):
            for _ in range(4):g.draw(.5,present=False)
        self.assertEqual(json.loads(json.dumps(capture(g))),before)

    def test_save_roundtrip_keeps_dead_enemies_aim_charge_and_flying_lasers(self):
        g=self.g;g.scorpions[0].ignite();enemy=g.scorpions[1]
        enemy.state='charge';enemy.angle=enemy.previous_angle=63.5;enemy.timer=.4
        g.laser_bolts=[LaserBolt(6450,400,330,-math.sqrt(660**2-330**2),.3)]
        data=json.loads(json.dumps(capture(g)));restore(g,data)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)
        self.assertFalse(g.scorpions[0].alive);self.assertEqual(g.scorpions[1].angle,63.5)
        self.assertEqual(len(g.laser_bolts),1);g.draw(1,present=False)

    def test_old_saves_without_scorpions_remain_loadable_and_invalid_bolts_are_rejected(self):
        g=self.g;data=capture(g);del data['scorpions'];del data['laser_bolts'];restore(g,data)
        self.assertEqual(len(g.scorpions),5);self.assertEqual(g.laser_bolts,[])
        bad=capture(g);bad['laser_bolts']=[dict(vars(LaserBolt(10,10,660,0)),vx=float('nan'))]
        with self.assertRaises(ValueError):validate(bad)

    def test_authored_turn_keeps_volume_in_front_view_and_renders_both_directions(self):
        g=self.g;sprites=g.scorpion_sprites;g.cam=g.prev_cam=850
        self.assertEqual(TURN_FRAMES,49)
        for face in (-1,1):
            widths=[sprites.areas[('turn',face,i)].w for i in range(TURN_FRAMES)]
            midpoint=TURN_FRAMES//2
            self.assertGreater(min(widths[midpoint-3:midpoint+4]),widths[0]*.7)
            enemy=g.scorpions[0];enemy.state='turn';enemy.turn_from=face
            with patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scaling')):
                for i in range(TURN_FRAMES):
                    enemy.timer=enemy.previous_timer=TURN_TIME*i/(TURN_FRAMES-1)
                    sprites.draw(g.canvas,enemy,g.cam,1)

    def test_turn_endpoints_match_walking_for_both_facings_and_incoming_gaits(self):
        sprites=self.g.scorpion_sprites
        def render(enemy):
            surface=pg.Surface((384,256),pg.SRCALPHA)
            sprites.draw(SimpleNamespace(native=surface),enemy,0,1)
            return pg.mask.from_surface(surface,32)
        for face in (-1,1):
            for gait in (0,7,19):
                enemy=Scorpion(0,((128,50,200,235/1.5,face),))
                enemy.distance=enemy.previous_distance=(gait+.1)*42/24
                before=render(enemy);enemy.turn_from=face;enemy.state='turn'
                start=render(enemy)
                self.assertEqual(before.count(),start.count())
                self.assertEqual(before.overlap_area(start,(0,0)),before.count())
                enemy.timer=enemy.previous_timer=TURN_TIME
                end=render(enemy);enemy.state='patrol';enemy.facing=-face
                enemy.distance=enemy.previous_distance=0
                after=render(enemy)
                self.assertEqual(end.count(),after.count())
                self.assertEqual(end.overlap_area(after,(0,0)),end.count())

    def test_raised_cannon_enters_turn_without_a_visual_snap(self):
        sprites=self.g.scorpion_sprites
        for face in (-1,1):
            enemy=Scorpion(0,((128,50,200,235/1.5,face),))
            enemy.angle=enemy.previous_angle=75;enemy.clock=enemy.previous_clock=1.8
            surfaces=[pg.Surface((384,256),pg.SRCALPHA) for _ in range(2)]
            sprites.draw(SimpleNamespace(native=surfaces[0]),enemy,0,1)
            enemy.state='turn';enemy.turn_from=face
            sprites.draw(SimpleNamespace(native=surfaces[1]),enemy,0,1)
            self.assertEqual(pg.image.tobytes(surfaces[0],'RGBA'),pg.image.tobytes(surfaces[1],'RGBA'))

    def test_tail_joins_the_rear_bearing_in_every_gait_and_facing(self):
        sprites=self.g.scorpion_sprites
        for face in (-1,1):
            for gait in range(24):
                enemy=Scorpion(0,((128,50,200,235/1.5,face),))
                enemy.distance=enemy.previous_distance=(gait+.1)*42/24
                body=sprites.images[sprites.pages[('body',face,gait)]].subsurface(sprites.areas[('body',face,gait)])
                ox,oy=sprites.offsets[('body',face,gait)]
                for clock in (0.,.8,2.5):
                    enemy.clock=enemy.previous_clock=clock
                    surface=pg.Surface((384,256),pg.SRCALPHA)
                    sprites.draw(SimpleNamespace(native=surface),enemy,0,1)
                    points=sprites.tail_points(clock,gait)
                    sx=round(192+face*points[0][0]*1.5);sy=round(235+points[0][1]*1.5)
                    bx=round(sx-(192-ox));by=round(sy-(235-oy))
                    # Independent window on the visible rear bearing in the
                    # source body: the old low root was near the leg instead.
                    source_x=bx if face>0 else body.get_width()-bx
                    self.assertTrue(29<=source_x<=41 and 12<=by<=26)
                    expected=body.get_at((bx,by));actual=surface.get_at((sx,sy))
                    # The source alpha is slightly translucent, so the link
                    # legitimately contributes at most its uncovered fraction.
                    self.assertLessEqual(max(abs(actual[i]-expected[i]) for i in range(3)),256-expected.a)
                    self.assertGreaterEqual(actual.a,expected.a)
                    # The rear bearing and every link must belong to the same
                    # opaque component; background must not split the chain.
                    component=pg.mask.from_surface(surface,32).connected_component((sx,sy))
                    for (ax,ay),(bx,by) in zip(points,points[1:]):
                        midpoint=(round(192+face*(ax+bx)*.75),round(235+(ay+by)*.75))
                        self.assertTrue(component.get_at(midpoint),(face,gait,clock,midpoint))

    def test_explosion_has_larger_flames_than_scarab_and_fades_completely(self):
        sprites=self.g.scorpion_sprites
        self.assertGreaterEqual(EXPLOSION_SIZE[0],120*3)
        self.assertGreaterEqual(DEATH_TIME,1.)
        widths=[]
        for face in (-1,1):
            for i in range(DEATH_FRAMES):
                key=('death',face,i)
                frame=sprites.images[sprites.pages[key]].subsurface(sprites.areas[key])
                if i==DEATH_FRAMES-1:self.assertEqual(pg.mask.from_surface(frame,0).count(),0)
                elif DEATH_FRAMES*.12<i<DEATH_FRAMES*.4:
                    # Warm fire pixels extend well beyond the old small flash.
                    fire=pg.mask.from_threshold(frame,(255,180,60,255),(90,130,65,255))
                    rects=fire.get_bounding_rects()
                    if rects:
                        bounds=rects[0].unionall(rects);widths.append(bounds.w)
        self.assertGreater(max(widths),120*2)

    def test_explosion_is_interpolated_preloaded_and_does_not_repeat(self):
        enemy=self.g.scorpions[0];sprites=self.g.scorpion_sprites;enemy.ignite()
        enemy.previous_death_timer=.1;enemy.death_timer=.3
        with patch.object(sprites,'stamp') as stamp:
            sprites.draw(self.g.canvas,enemy,850,0)
            first=stamp.call_args.args[1]
            sprites.draw(self.g.canvas,enemy,850,1)
            second=stamp.call_args.args[1]
            self.assertLess(first[-1],second[-1])
            enemy.previous_death_timer=enemy.death_timer=DEATH_TIME
            stamp.reset_mock();sprites.draw(self.g.canvas,enemy,850,1);stamp.assert_not_called()
        self.assertFalse(enemy.ignite());self.assertFalse(enemy.alive)
