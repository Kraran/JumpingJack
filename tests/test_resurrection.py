import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from resurrection import FLASH_AT,REAPPEAR,DURATION
from lives import life_position
from savegame import capture,restore,validate
from support import finish_respawn


class ResurrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.state='play'

    def die(self,level=1,lives=3):
        g=self.g;g.start_level(level);g.state='play';g.lives=lives
        g.hero.y=g.world_height+200 if level==4 else 900
        g.update(STEP,0,False,False)
        while g.hero_death.active:g.update(STEP,0,False,False)

    def test_icon_leaves_the_consumed_hud_slot_and_grows_into_the_screen_center(self):
        g=self.g;self.die()
        self.assertEqual((g.lives,g.deaths),(2,1));self.assertTrue(g.resurrection.active)
        self.assertEqual(g.resurrection.life_index,2)
        rect=g.resurrection_sprites.geometry(g.resurrection)
        x,y=g.canvas.point(life_position(2))
        self.assertEqual(rect.topleft,(x,y));self.assertEqual(rect.size,g.life_symbol.get_size())
        g.resurrection.previous_elapsed=g.resurrection.elapsed=FLASH_AT
        giant=g.resurrection_sprites.geometry(g.resurrection)
        self.assertEqual(giant.center,(960,540));self.assertGreater(giant.w,1000)

    def test_hero_appears_once_at_the_flash_in_all_four_levels(self):
        g=self.g
        for level in range(1,5):
            with self.subTest(level=level):
                self.die(level);old_hero=g.hero
                with patch.object(g,'respawn_hero',wraps=g.respawn_hero) as respawn:
                    while g.resurrection.elapsed<REAPPEAR-2*STEP:g.update(STEP,1,True,True,fire=True)
                    self.assertIs(g.hero,old_hero);respawn.assert_not_called();self.assertFalse(g.solar.active)
                    while not g.resurrection.spawned:g.update(STEP,0,False,False)
                    g.time=.1  # Ordinarily an invisible phase of the grace-period blink.
                    with patch.object(g,'draw_hero',wraps=g.draw_hero) as draw_hero:
                        g.draw(1,present=False);draw_hero.assert_called_once()
                    finish_respawn(g)
                    respawn.assert_called_once_with()
                self.assertIsNot(g.hero,old_hero);self.assertEqual((g.hero.x,g.hero.y),g.checkpoint)
                self.assertEqual(g.deaths,1);self.assertGreater(g.invuln,0)
                self.assertTrue(g.menu_gameplay_blocked)

    def test_pause_save_and_old_slots_preserve_resurrection_without_spawning_twice(self):
        g=self.g;self.die()
        for _ in range(25):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=json.loads(json.dumps(capture(g)))
        for _ in range(10):g.update(STEP,0,False,False)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)
        restore(g,data);self.assertEqual(json.loads(json.dumps(capture(g))),data)
        g.resume_from_menu()
        while not g.resurrection.spawned:g.update(STEP,0,False,False)
        after=capture(g);restore(g,after)
        with patch.object(g,'respawn_hero',wraps=g.respawn_hero) as spawn:finish_respawn(g);spawn.assert_not_called()
        legacy=capture(g);del legacy['resurrection'];restore(g,legacy);self.assertFalse(g.resurrection.active)
        bad=json.loads(json.dumps(data));bad['resurrection']['spawned']=True
        with self.assertRaises(ValueError):validate(bad)

    def test_last_life_has_no_resurrection_and_crocodile_finishes_before_zoom(self):
        g=self.g;self.die(lives=1)
        self.assertEqual(g.state,'game_over');self.assertFalse(g.resurrection.active)
        g.new_game();g.state='play';enemy=g.crocodiles[0];g.hero=Hero(enemy.x,enemy.y)
        g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertFalse(g.resurrection.active)
        while g.hero_death.active:g.update(STEP,0,False,False)
        self.assertTrue(g.resurrection.active);self.assertEqual(g.resurrection.elapsed,0)
        finish_respawn(g);self.assertEqual((g.lives,g.deaths),(2,1))

    def test_drawing_is_read_only_and_flash_covers_respawn(self):
        g=self.g;self.die()
        for t in (0,.4,FLASH_AT,REAPPEAR,1.1):
            g.resurrection.elapsed=g.resurrection.previous_elapsed=t
            before=json.loads(json.dumps(capture(g)))
            g.draw(1,present=False)
            self.assertEqual(json.loads(json.dumps(capture(g))),before)
            if t==REAPPEAR:self.assertEqual(tuple(g.native_canvas.surface.get_at((960,540)))[:3],(255,250,225))

    def test_crocodile_holds_its_final_pose_until_the_respawn_flash(self):
        g=self.g
        for level in (1,2):
            for side in (-1,1):
                with self.subTest(level=level,side=side):
                    g.new_game();g.start_level(level);g.state='play'
                    enemy=g.crocodiles[0]
                    enemy.state=enemy.previous_state='lunge'
                    enemy.facing=enemy.previous_facing=-side
                    g.hero=Hero(enemy.x+side*40,enemy.y);g.hero.grounded=True
                    g.cam=g.prev_cam=max(0,enemy.x-450)
                    g.update(STEP,0,False,False)
                    while g.hero_death.active:g.update(STEP,0,False,False)
                    self.assertTrue(g.resurrection.active)
                    for alpha in (0,.2,.5,.9,1):
                        with patch.object(g.hero_death_sprites,'draw',wraps=g.hero_death_sprites.draw) as death_draw:
                            g.draw_crocodiles(g.cam,alpha)
                        death_draw.assert_called_once()
                        self.assertEqual(death_draw.call_args.args[3],1)
                    self.assertEqual(g.prev_cam,g.cam)
                    for _ in range(20):g.update(STEP,0,False,False)
                    g.enter_menu('pause');data=json.loads(json.dumps(capture(g)));restore(g,data)
                    enemy=g.crocodiles[0]
                    with patch.object(g.hero_death_sprites,'draw',wraps=g.hero_death_sprites.draw) as death_draw:
                        g.draw_crocodiles(g.cam,.4)
                    death_draw.assert_called_once()
                    self.assertEqual(json.loads(json.dumps(capture(g))),data)
                    g.resume_from_menu()
                    while not g.resurrection.spawned:g.update(STEP,0,False,False)
                    with patch.object(g.hero_death_sprites,'draw') as death_draw:
                        g.draw_crocodiles(g.cam,.4)
                    death_draw.assert_not_called()
                    self.assertEqual(enemy.state,'patrol');self.assertEqual(enemy.px,enemy.x)
                    finish_respawn(g)
                    self.assertEqual((g.lives,g.deaths),(2,1))
