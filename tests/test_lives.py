import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from gamepad import PadSnapshot


class LivesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.state='play'

    def die(self):
        self.g.hero.y=900
        self.g.update(STEP,0,False,False)

    def test_three_lives_two_respawns_then_game_over_and_frozen_world(self):
        g=self.g;g.checkpoint=(4740,620)
        self.assertEqual(g.lives,3)
        for remaining in (2,1):
            self.die()
            self.assertEqual(g.lives,remaining);self.assertEqual(g.state,'play')
            self.assertEqual(g.hero.x,4740);self.assertGreater(g.invuln,0)
        with patch.object(g.gamepads,'rumble') as rumble:
            self.die();rumble.assert_called_once_with('death')
        self.assertEqual(g.lives,0);self.assertEqual(g.deaths,3);self.assertEqual(g.state,'game_over')
        self.assertEqual(g.hero.y,900+1550*STEP*STEP)
        before=(g.elapsed,g.hero.x,g.hero.y,g.deaths)
        for _ in range(20):g.update(STEP,1,True,True,fire=True)
        self.assertEqual(before,(g.elapsed,g.hero.x,g.hero.y,g.deaths))

    def test_platform_spike_and_enemy_contact_each_cost_only_one_life(self):
        g=self.g
        for kind in ('spike','enemy'):
            g.new_game();g.state='play'
            if kind=='spike':
                with patch.object(Hero,'update',autospec=True,side_effect=lambda hero,*args,**kw:setattr(hero,'spike_hit',True)):
                    g.update(STEP,0,False,False)
            else:
                x,y=g.enemy_positions()[0];g.hero=Hero(x,y+27)
                g.update(STEP,0,False,False)
            self.assertEqual(g.lives,2);self.assertEqual(g.deaths,1)
            g.update(STEP,0,False,False)
            self.assertEqual(g.lives,2)

    def test_restart_level_preserves_lives_and_medallions_new_game_resets_them(self):
        g=self.g;g.medallions.collect();self.die()
        g.handle_pad(PadSnapshot(back_pressed=True))
        self.assertEqual(g.lives,2);self.assertEqual(g.medallions.count,1)
        self.assertFalse(g.medallions.available())
        for _ in range(2):self.die()
        g.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True))
        self.assertEqual(g.state,'play');self.assertEqual(g.lives,3)
        self.assertEqual(g.medallions.count,0);self.assertTrue(g.medallions.available())
        self.assertEqual(g.deaths,0);self.assertFalse(g.pending_jump)

    def test_start_and_keyboard_enter_restart_game_over(self):
        g=self.g
        self.die();self.die();self.die()
        g.handle_pad(PadSnapshot(start_pressed=True))
        self.assertEqual((g.state,g.lives),('play',3))
        self.die();self.die();self.die()
        import pygame as pg
        pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN))
        # run closes the display; keep it open for the shared fixture.
        with patch.object(g,'close'),patch.object(g.pacer,'wait'):
            g.run(frames=1)
        self.assertEqual((g.state,g.lives),('play',3))

    def test_all_three_enemy_types_stay_dead_between_lives_until_level_or_game_restart(self):
        from beetle import BeetleDeath
        g=self.g
        for restart in (g.reset,g.new_game):
            g.new_game();g.state='play'
            g.dead_beetles.add(0);g.beetle_deaths.append(BeetleDeath(1920,495,-1))
            crocodile=g.crocodiles[0];guardian=g.vultures[0]
            crocodile.ignite();guardian.ignite()
            for remaining in (2,1):
                self.die();self.assertEqual(g.lives,remaining)
                self.assertEqual(g.dead_beetles,{0})
                self.assertNotIn(0,[index for index,_,_ in g.beetles()])
                self.assertIs(g.crocodiles[0],crocodile);self.assertFalse(crocodile.alive)
                self.assertIs(g.vultures[0],guardian);self.assertFalse(guardian.alive)
                self.assertTrue(all(enemy.alive for enemy in g.crocodiles[1:]))
                self.assertTrue(all(enemy.alive for enemy in g.vultures[1:]))
                self.assertGreater(crocodile.death_timer,0);self.assertGreater(guardian.timer,0)
            restart()
            self.assertFalse(g.dead_beetles);self.assertFalse(g.beetle_deaths)
            self.assertTrue(all(enemy.alive for enemy in g.crocodiles+g.vultures))
    def test_hud_uses_actual_chest_symbol_and_game_over_render_is_read_only(self):
        g=self.g;g.prepare_rendering()
        self.assertGreater(g.life_symbol.get_bounding_rect().w,20)
        with patch.object(g.canvas,'blit_native',wraps=g.canvas.blit_native) as blit:
            g.hud()
            self.assertEqual(sum(c.args[0] is g.life_symbol for c in blit.call_args_list),3)
        self.die();self.die();self.die()
        before=(g.lives,g.deaths,g.elapsed)
        texts=set(g.text_cache)
        with patch.object(g,'text',wraps=g.text) as text:
            g.draw(1,present=False)
            self.assertTrue(any(c.args[0]=='GAME OVER' for c in text.call_args_list))
        self.assertEqual(before,(g.lives,g.deaths,g.elapsed));self.assertEqual(texts,set(g.text_cache))

    def test_game_over_during_solar_shot_draws_ground_air_and_crouched_poses(self):
        g=self.g
        for stance in ('ground','air','crouch'):
            with self.subTest(stance=stance):
                g.new_game();g.state='play';g.lives=1
                g.hero=Hero(160,300 if stance=='air' else 620)
                g.hero.grounded=stance!='air'
                if stance=='crouch':g.hero.crouch=g.hero.previous_crouch=1.
                def contact():return [(g.hero.x,g.hero.y-g.hero.body_height/2)]
                with patch.object(g,'enemy_positions',side_effect=contact):
                    g.update(STEP,0,False,False,fire=True,down=stance=='crouch')
                self.assertEqual((g.state,g.lives),('game_over',0))
                self.assertFalse(g.solar.active)
                for alpha in (0,.5,1):g.draw(alpha,present=False)


if __name__=='__main__':unittest.main()
