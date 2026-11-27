import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from gamepad import PadSnapshot
from support import finish_respawn


class LivesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.state='play'

    def die(self):
        self.g.hero.y=900
        self.g.update(STEP,0,False,False)
        finish_respawn(self.g)

    def test_death_clears_old_explosions_and_particles_without_reviving_beetles(self):
        from beetle import BeetleDeath
        g=self.g
        for lives in (2,1):
            with self.subTest(lives=lives):
                g.new_game();g.state='play';g.lives=lives
                g.dead_beetles.add(0)
                g.beetle_deaths.append(BeetleDeath(1920,495,-1))
                g.burst(1920,495,(1,2,3),12)
                self.die()
                self.assertFalse(g.beetle_deaths)
                self.assertEqual(g.dead_beetles,{0})
                self.assertNotIn(0,[index for index,_,_ in g.beetles()])
                self.assertFalse(any(particle[5]==(1,2,3) for particle in g.particles))
                if lives>1:
                    self.assertEqual(g.state,'play')
                    self.assertTrue(g.particles);self.assertLessEqual(len(g.particles),24)
                    self.assertTrue(all(particle[5]==(130,224,227) for particle in g.particles))
                else:
                    self.assertEqual(g.state,'game_over')
                    self.assertFalse(g.particles)

    def test_three_lives_two_respawns_then_game_over_and_frozen_world(self):
        g=self.g;g.checkpoint=(4740,620)
        self.assertEqual(g.lives,3)
        for remaining in (2,1):
            self.die()
            self.assertEqual(g.lives,remaining);self.assertEqual(g.state,'play')
            self.assertEqual(g.hero.x,4740);self.assertGreater(g.invuln,0)
        with patch.object(g.gamepads,'rumble') as rumble:
            self.die()
            self.assertEqual([(call.args,call.kwargs) for call in rumble.call_args_list],
                             [(('death',),{'duration':750}),(('game_over',),{})])
        self.assertEqual(g.lives,0);self.assertEqual(g.deaths,3);self.assertEqual(g.state,'game_over')
        self.assertGreater(g.hero.y,900)
        self.assertEqual(g.hero_death.kind,'pit')
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

    def test_level_transition_replaces_old_checkpoint_and_death_stays_in_new_level(self):
        g=self.g
        for target in range(2,9):
            with self.subTest(level=target):
                g.new_game();g.start_level(target-1)
                g.checkpoint=(g.obelisks[-1].x-60,g.obelisks[-1].y)
                g.check_index=len(g.obelisks);g.obelisks[-1].active=True
                g.state='win';g.continue_or_restart()
                entrance=(g.hero.x,g.hero.y)
                self.assertEqual(g.checkpoint,entrance)
                self.assertEqual(g.check_index,0)
                self.assertFalse(any(obelisk.active for obelisk in g.obelisks))
                g.hero.x+=800;g.kill_hero();finish_respawn(g)
                self.assertEqual((g.level_id,g.lives,g.state),(target,2,'play'))
                self.assertEqual((g.hero.x,g.hero.y),entrance)

    def test_game_over_restarts_campaign_at_level_one_for_keyboard_and_controller(self):
        import pygame as pg
        g=self.g
        for target in range(1,9):
            for controller in (False,True):
                with self.subTest(level=target,controller=controller):
                    g.new_game();g.start_level(target);g.state='play';g.lives=1
                    entrance=(Hero().x,Hero().y)
                    g.checkpoint=(g.obelisks[-1].x-60,g.obelisks[-1].y)
                    g.check_index=len(g.obelisks)
                    g.kill_hero();self.assertEqual(g.state,'game_over')
                    if controller:g.handle_pad(PadSnapshot(start_pressed=True))
                    else:
                        pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN))
                        with patch.object(g,'close'),patch.object(g.pacer,'wait'):
                            g.run(frames=1)
                    self.assertEqual((g.state,g.level_id,g.lives),('play',1,3))
                    self.assertEqual((g.hero.x,g.hero.y),entrance)
                    self.assertEqual(g.checkpoint,entrance);self.assertEqual(g.check_index,0)
                    self.assertFalse(g.pending_jump)

    def test_save_before_first_obelisk_retains_level_entrance_after_loading_and_death(self):
        from savegame import capture,restore
        g=self.g
        for target in range(2,9):
            with self.subTest(level=target):
                g.new_game();g.start_level(target);g.state='play'
                entrance=(g.hero.x,g.hero.y)
                g.hero.x+=100
                data=capture(g)
                g.new_game();restore(g,data);g.state='play'
                g.kill_hero();finish_respawn(g)
                self.assertEqual(g.level_id,target)
                self.assertEqual((g.hero.x,g.hero.y),entrance)
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
