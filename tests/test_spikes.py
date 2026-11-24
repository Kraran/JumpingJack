import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch,call,MagicMock
from main import Hero,Platform,Game,STEP,WORLD,level,PLATFORM_WIDTHS
from spikes import upward_contact,SPIKE_DEPTH,SPIKED_PLATFORM_X,SPIKE_PITCH,teeth
from gamepad import ControllerPad,JoystickPad,RUMBLE_EFFECTS


class SpikePhysicsTests(unittest.TestCase):
    def test_one_fewer_tooth_and_centered_clearance_at_both_beveled_edges(self):
        for width in PLATFORM_WIDTHS:
            platform=Platform(200,300,width,32,spiked=True);row=list(teeth(platform))
            self.assertEqual(len(row),int(width/SPIKE_PITCH)-1)
            left_margin=row[0][0]-platform.x
            right_margin=platform.x+width-row[-1][1]
            self.assertAlmostEqual(left_margin,right_margin)
            self.assertGreaterEqual(left_margin,14)

    def test_only_four_platforms_in_second_half_have_spikes_and_ground_route_is_clear(self):
        platforms,_=level();hazards=[p for p in platforms if p.spiked]
        self.assertEqual({p.x for p in hazards},set(SPIKED_PLATFORM_X))
        self.assertEqual(len(hazards),4)
        self.assertTrue(all(not p.ground and p.x>WORLD/2 for p in hazards))
        self.assertTrue(all(p.y+p.h+SPIKE_DEPTH<620-54 for p in hazards))

    def test_upward_head_hits_point_before_platform_and_does_not_bong(self):
        p=Platform(200,300,120,32,spiked=True)
        hero=Hero(212,420);hero.vy=-600
        hero.update(.04,0,False,False,[p])
        self.assertTrue(hero.spike_hit);self.assertFalse(hero.head_bump)
        self.assertEqual(hero.y-hero.body_height,p.y+p.h+SPIKE_DEPTH)

    def test_sweep_catches_high_speed_upward_crossing(self):
        p=Platform(200,300,120,32,spiked=True)
        hero=Hero(212,454);hero.vy=-950
        hero.update(.15,0,False,False,[p])
        self.assertTrue(hero.spike_hit)

    def test_lower_solid_platform_shields_spikes_behind_it(self):
        p=Platform(200,300,120,32,spiked=True);shield=Platform(150,350,250,32)
        hero=Hero(212,454);hero.vy=-950
        hero.update(.15,0,False,False,[p,shield])
        self.assertFalse(hero.spike_hit);self.assertTrue(hero.head_bump)
        self.assertEqual(hero.y-hero.body_height,382)

    def test_side_and_descending_contacts_are_not_deadly(self):
        p=Platform(200,300,120,32,spiked=True)
        for vy,held in ((0,False),(105,True),(250,False)):
            hero=Hero(184,350);hero.vx=340;hero.vy=vy
            hero.update(STEP,1,held,False,[p])
            self.assertFalse(hero.spike_hit)
        hero=Hero(212,410);hero.vy=100
        hero.update(STEP,0,False,False,[p]);self.assertFalse(hero.spike_hit)
        self.assertIsNone(upward_contact(p,184,370,340))

    def test_deliberate_drop_through_spiked_source_is_safe_until_landing(self):
        p=Platform(200,300,120,32,spiked=True);floor=Platform(0,620,1000,140,True)
        hero=Hero(250,300);hero.grounded=True
        for tick in range(120):
            hero.update(STEP,0,True,tick==0,[p,floor],drop=tick==0)
            self.assertFalse(hero.spike_hit)
            if hero.grounded and hero.y==620:break
        self.assertTrue(hero.grounded);self.assertEqual(hero.y,620)

    def test_ordinary_platform_still_only_bumps_head(self):
        hero=Hero(212,420);hero.vy=-600
        for _ in range(10):
            hero.update(STEP,0,False,False,[Platform(200,300,120,32)])
            self.assertFalse(hero.spike_hit)
            if hero.head_bump:break
        self.assertTrue(hero.head_bump)


class SpikeGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.state='play'

    def test_upward_hit_kills_even_during_grace_and_respawns_at_checkpoint(self):
        g=self.g;g.reset();g.state='play';g.invuln=100;g.checkpoint=(4740,620)
        g.platforms=[Platform(200,300,120,32,spiked=True)]
        g.hero=Hero(212,420);g.hero.vy=-600
        with patch.object(g.gamepads,'rumble') as rumble,patch.object(g,'sound') as sound:
            for _ in range(10):
                g.update(STEP,0,False,False)
                if g.deaths:break
            rumble.assert_called_once_with('death')
            self.assertNotIn(call('bong'),sound.call_args_list)
        self.assertEqual(g.deaths,1);self.assertEqual((g.hero.x,g.hero.y),g.checkpoint)
        self.assertFalse(g.hero.spike_hit)

    def test_render_uses_preloaded_atlas_only_for_spiked_platforms(self):
        g=self.g;g.reset()
        with patch.object(g.spike_sprites,'draw') as render:
            for p in g.platforms:g.platform(p,p.x)
        self.assertEqual(render.call_count,4)
        self.assertEqual(len(g.spike_sprites.images),1)

    def test_blade_death_sends_full_strength_death_vibration_to_both_pad_backends(self):
        g=self.g;original_devices=g.gamepads.devices
        try:
            for adapter in (ControllerPad,JoystickPad):
                g.reset();g.state='play';g.invuln=100
                raw=MagicMock();raw.name='Test';raw.rumble.return_value=True
                g.gamepads.devices={7:adapter(raw)}
                g.platforms=[Platform(200,300,120,32,spiked=True)]
                g.hero=Hero(224,420);g.hero.vy=-600
                for _ in range(10):
                    g.update(STEP,0,False,False)
                    if g.deaths:break
                self.assertEqual(g.deaths,1)
                raw.rumble.assert_called_once_with(*RUMBLE_EFFECTS['death'])
                self.assertEqual(RUMBLE_EFFECTS['death'],(1.,1.,400))
        finally:g.gamepads.devices=original_devices
