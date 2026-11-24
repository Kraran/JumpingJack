import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch,MagicMock
from energy import SolarEnergy,MAX_ENERGY,GLIDE_PER_SECOND,RAY_COST,SHARD_ENERGY
from solar import SolarRay
from main import Game,Hero,STEP


class EnergyBudgetTests(unittest.TestCase):
    def test_starts_full_and_glide_is_time_based(self):
        for hz in (60,120,144):
            energy=SolarEnergy()
            self.assertEqual(energy.value,MAX_ENERGY)
            for _ in range(hz*3):energy.drain_glide(1/hz)
            self.assertAlmostEqual(energy.value,MAX_ENERGY-3*GLIDE_PER_SECOND)

    def test_ray_debits_once_and_rejected_or_cooldown_inputs_are_free(self):
        energy=SolarEnergy();hero=Hero();ray=SolarRay()
        ray.update(STEP,hero,True,energy)
        self.assertEqual(energy.value,MAX_ENERGY-RAY_COST)
        for _ in range(60):ray.update(STEP,hero,True,energy)
        self.assertEqual(energy.value,MAX_ENERGY-RAY_COST)
        ray.reset();hero.floating=True
        ray.update(STEP,hero,True,energy)
        self.assertEqual(energy.value,MAX_ENERGY-RAY_COST)

    def test_insufficient_energy_plays_gesture_without_beam_or_sound(self):
        for budget in (0,RAY_COST-.01):
            energy=SolarEnergy();energy.value=budget
            hero=Hero();ray=SolarRay()
            fired=ray.update(STEP,hero,True,energy)
            self.assertTrue(ray.active);self.assertGreater(ray.cooldown,0)
            self.assertEqual(energy.value,budget)
            self.assertGreater(energy.warning,0)
            for _ in range(47):
                fired=ray.update(STEP,hero,False,energy) or fired
                self.assertFalse(ray.emitting)
                self.assertIsNone(ray.visual_elapsed)
            self.assertFalse(fired);self.assertFalse(ray.active)

    def test_dry_fire_draws_no_charge_or_plasma_on_either_backend(self):
        for effect in (None,MagicMock()):
            energy=SolarEnergy();energy.value=0
            hero=Hero();ray=SolarRay(effect)
            ray.update(.2,hero,True,energy)
            with patch('solar.draw') as primitives:
                ray.draw(MagicMock(),hero,[],alpha=.5)
            self.assertEqual(primitives.mock_calls,[])
            if effect is not None:effect.draw.assert_not_called()

    def test_collecting_during_dry_fire_requires_a_new_shot(self):
        energy=SolarEnergy();energy.value=20
        hero=Hero();ray=SolarRay();ray.update(STEP,hero,True,energy)
        energy.collect();self.assertEqual(energy.value,30)
        for _ in range(80):
            self.assertFalse(ray.update(STEP,hero,False,energy))
            self.assertFalse(ray.emitting)
        ray.update(STEP,hero,True,energy)
        self.assertTrue(ray.powered);self.assertEqual(energy.value,0)

    def test_exact_ray_budget_is_allowed_and_never_negative(self):
        energy=SolarEnergy();energy.value=RAY_COST
        self.assertTrue(energy.spend_ray());self.assertEqual(energy.value,0)
        self.assertFalse(energy.spend_ray());energy.drain_glide(100)
        self.assertEqual(energy.value,0)

    def test_collect_recharges_and_caps_at_maximum(self):
        energy=SolarEnergy();energy.value=7
        energy.collect();self.assertEqual(energy.value,7+SHARD_ENERGY)
        for _ in range(20):energy.collect()
        self.assertEqual(energy.value,MAX_ENERGY)

    def test_ray_display_moves_rapidly_but_never_jumps_or_overshoots(self):
        energy=SolarEnergy();energy.spend_ray()
        self.assertEqual(energy.display,MAX_ENERGY)
        seen=[]
        for _ in range(12):energy.update_display(STEP);seen.append(energy.display)
        self.assertTrue(all(energy.value<=v<MAX_ENERGY for v in seen))
        self.assertEqual(seen,sorted(seen,reverse=True))
        self.assertLess(energy.display-energy.value,1)
        self.assertGreater(energy.fraction(0),energy.fraction(1))

    def test_refill_animates_and_clears_insufficient_warning(self):
        energy=SolarEnergy();energy.value=energy.display=energy.previous_display=0
        energy.spend_ray();energy.refill()
        self.assertEqual(energy.warning,0)
        self.assertEqual(energy.display,0)
        energy.update_display(STEP)
        self.assertTrue(0<energy.display<MAX_ENERGY)


class EnergyGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.reset();self.g.state='play';self.g.invuln=10

    def test_collection_recharges_once_and_same_step_can_pay_for_ray(self):
        x,y=self.g.gems[0];self.g.hero=Hero(x,y+28)
        self.g.energy.value=RAY_COST-SHARD_ENERGY
        self.g.update(STEP,0,False,False,fire=True)
        self.assertIn(0,self.g.taken);self.assertTrue(self.g.solar.active)
        self.assertAlmostEqual(self.g.energy.value,0)
        self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.energy.value,0)

    def test_gliding_drains_and_empty_energy_resumes_normal_fall(self):
        self.g.hero=Hero(100,100);self.g.hero.vy=105
        self.g.energy.value=GLIDE_PER_SECOND*STEP*2
        self.g.update(STEP,0,True,False)
        self.assertTrue(self.g.hero.floating)
        self.g.update(STEP,0,True,False)
        self.assertEqual(self.g.energy.value,0)
        self.g.update(STEP,0,True,False)
        self.assertFalse(self.g.hero.floating)
        self.assertGreater(self.g.hero.vy,105)

    def test_standing_and_jumping_do_not_consume_energy(self):
        self.g.hero=Hero(100,620);self.g.hero.grounded=True
        self.g.energy.value=0
        self.g.update(STEP,0,True,True)
        self.assertLess(self.g.hero.vy,0)
        self.assertEqual(self.g.energy.value,0)

    def test_rest_wakeup_fire_is_consumed_without_energy_cost(self):
        self.g.rest.state='seated';self.g.rest.progress=1
        self.g.update(STEP,0,False,False,fire=True)
        for _ in range(100):self.g.update(STEP,0,False,False)
        self.assertFalse(self.g.solar.active)
        self.assertEqual(self.g.energy.value,MAX_ENERGY)

    def test_no_passive_regeneration(self):
        self.g.hero=Hero(100,620);self.g.hero.grounded=True
        self.g.energy.value=20
        for _ in range(800):self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.energy.value,20)

    def test_dry_fire_animates_on_ground_and_in_air_without_harming_enemy(self):
        for grounded in (True,False):
            self.g.reset();self.g.invuln=10
            self.g.hero=Hero(700,620 if grounded else 400)
            self.g.hero.grounded=grounded;self.g.energy.value=0
            with patch.object(self.g,'sound') as sound:
                for tick in range(47):
                    self.g.update(STEP,0,False,False,fire=tick==0)
                    self.assertEqual(self.g.hero_animation.state,'solar_ground' if grounded else 'solar_air')
                    self.assertTrue(self.g.crocodiles[0].alive)
                self.assertNotIn(unittest.mock.call('solar'),sound.call_args_list)
            self.assertEqual(self.g.energy.value,0)

    def test_death_refills_and_restart_starts_with_full_gauge(self):
        self.g.energy.value=self.g.energy.display=10
        self.g.hero.y=900;self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.energy.value,MAX_ENERGY)
        self.assertTrue(10<self.g.energy.display<MAX_ENERGY)
        self.g.energy.value=0;self.g.reset()
        self.assertEqual(self.g.energy.value,MAX_ENERGY)
        self.assertEqual(self.g.energy.display,MAX_ENERGY)

    def test_pause_freezes_energy_and_display(self):
        self.g.energy.spend_ray();self.g.energy.update_display(STEP)
        self.g.state='pause';before=(self.g.energy.value,self.g.energy.display,self.g.energy.fast_timer)
        with patch.object(self.g,'close'),patch('main.pg.event.get',return_value=[]):self.g.run(frames=2)
        self.assertEqual(before,(self.g.energy.value,self.g.energy.display,self.g.energy.fast_timer))

    def test_gauge_draw_is_read_only_for_every_interpolation_phase(self):
        self.g.energy.spend_ray();self.g.energy.update_display(STEP)
        before=(self.g.energy.value,self.g.energy.display,self.g.energy.previous_display)
        for alpha in (0,.25,.5,.75,1):self.g.draw(alpha)
        self.assertEqual(before,(self.g.energy.value,self.g.energy.display,self.g.energy.previous_display))


if __name__=='__main__':unittest.main()
