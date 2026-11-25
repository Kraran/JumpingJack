import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
import pygame as pg
from main import Game,STEP
from gamepad import ControllerPad,Gamepads,PadSnapshot
from settings import Settings


class SettingsTests(unittest.TestCase):
    @patch('settings.detect_system_language',return_value='fr')
    def test_round_trip_and_bad_files_use_validated_defaults(self,detect):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            self.assertEqual(Settings.load(path),Settings())
            choices=Settings(False,False,False,True)
            self.assertTrue(choices.save(path));self.assertEqual(Settings.load(path),choices)
            self.assertFalse(path.with_suffix('.json.tmp').exists())
            for content in ('broken','[]','null','{"sound": 0, "rumble": "false", "unknown": true}'):
                path.write_text(content,encoding='utf-8')
                expected='fr' if content.startswith('{') else 'en'
                self.assertEqual(Settings.load(path),Settings(language=expected))

    def test_failed_save_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json';Settings().save(path)
            with patch('settings.Path.replace',side_effect=OSError('read only')):
                self.assertFalse(Settings(sound=False).save(path))
            self.assertTrue(Settings.load(path).sound)

    def test_game_loads_sound_vibration_and_fps_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json';Settings(False,False,False,True).save(path)
            game=Game(True,settings_path=path)
            try:
                self.assertFalse(game.fullscreen);self.assertFalse(game.sound_on)
                self.assertFalse(game.gamepads.rumble_enabled);self.assertTrue(game.show_fps)
                game.draw(1,present=False)
            finally:game.close()


class MenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        g=self.g;g.new_game();g.state='title';g.quit_requested=False
        g.menu.selected={page:0 for page in g.menu.selected}
        g.menu.origin='title';g.menu.enter('title');g.menu.save_failed=False
        g.sound_on=True;g.show_fps=False;g.show_stats=False;g.gamepads.rumble_enabled=True
        g.settings_path=None;g.settings=Settings();g.time=0
        g.pad=PadSnapshot()

    def run_events(self,events=(),pad=None,frames=1):
        g=self.g
        with patch.object(g,'close') as close,patch.object(g.pacer,'wait'),\
             patch('main.pg.event.get',return_value=list(events)),\
             patch.object(g.gamepads,'poll',return_value=pad or PadSnapshot()):
            g.run(frames=frames)
            close.assert_called_once()

    def test_keyboard_enters_settings_commands_and_returns_without_starting(self):
        g=self.g;before=(g.elapsed,g.hero.x,g.hero.y)
        g.menu_key(pg.K_DOWN);g.menu_key(pg.K_RETURN)
        self.assertEqual(g.state,'settings')
        for _ in range(4):g.menu_key(pg.K_DOWN)
        g.menu_key(pg.K_RETURN);self.assertEqual(g.state,'controls')
        g.menu_key(pg.K_ESCAPE);self.assertEqual(g.state,'settings')
        g.menu_key(pg.K_ESCAPE);self.assertEqual(g.state,'title')
        self.assertEqual(before,(g.elapsed,g.hero.x,g.hero.y))

    def test_dpad_up_does_not_confirm_and_a_b_are_separate_from_dpad_and_trigger(self):
        g=self.g;raw=MagicMock();raw.id=4;raw.name='Test'
        buttons={pg.CONTROLLER_BUTTON_DPAD_UP:True};axes={}
        raw.get_button.side_effect=lambda key:buttons.get(key,False)
        raw.get_axis.side_effect=lambda key:axes.get(key,0)
        pads=Gamepads(False);pads.devices={4:ControllerPad(raw)}
        g.handle_pad(pads.poll())
        self.assertEqual(g.state,'title');self.assertEqual(g.menu.selected['title'],3)
        self.assertFalse(g.quit_requested)
        g.menu.selected['title']=1
        buttons.clear();buttons[pg.CONTROLLER_BUTTON_A]=True
        g.handle_pad(pads.poll());self.assertEqual(g.state,'settings')
        buttons.clear();axes[pg.CONTROLLER_AXIS_TRIGGERRIGHT]=25000
        sample=pads.poll();self.assertTrue(sample.fire_pressed);self.assertFalse(sample.cancel_pressed)
        g.handle_pad(sample);self.assertEqual(g.state,'settings')
        buttons[pg.CONTROLLER_BUTTON_B]=True
        g.handle_pad(pads.poll());self.assertEqual(g.state,'title')

    def test_stick_navigation_repeats_after_delay_and_wraps(self):
        g=self.g
        for now,expected in ((0,1),(.1,1),(.33,2),(.47,3),(.61,0)):
            g.time=now;g.handle_pad(PadSnapshot(menu_axis=1))
            self.assertEqual(g.menu.selected['title'],expected)
        g.handle_pad(PadSnapshot());g.handle_pad(PadSnapshot(menu_axis=-1))
        self.assertEqual(g.menu.selected['title'],3)

    def test_holding_horizontal_changes_boolean_setting_only_once(self):
        g=self.g;g.enter_menu('settings');g.menu.selected['settings']=1
        for now in (0,.1,.5,1.):
            g.time=now;g.handle_pad(PadSnapshot(axis=1))
            self.assertFalse(g.sound_on)
        g.handle_pad(PadSnapshot());g.handle_pad(PadSnapshot(axis=1))
        self.assertTrue(g.sound_on)

    def test_options_apply_and_save_sound_vibration_fps_and_display(self):
        g=self.g;g.enter_menu('settings')
        with tempfile.TemporaryDirectory() as directory:
            g.settings_path=Path(directory)/'settings.json'
            for index in (1,2,3):
                g.menu.selected['settings']=index;g.menu_action('right')
            loaded=Settings.load(g.settings_path)
            self.assertFalse(g.sound_on);self.assertFalse(g.gamepads.rumble_enabled)
            self.assertTrue(g.show_fps);self.assertEqual((loaded.sound,loaded.rumble,loaded.show_fps),(False,False,True))
            raw=MagicMock();devices=g.gamepads.devices;g.gamepads.devices={1:raw}
            try:
                self.assertFalse(g.gamepads.rumble('death'));raw.rumble.assert_not_called()
            finally:g.gamepads.devices=devices
            g.menu.selected['settings']=0
            with patch.object(g,'toggle_fullscreen') as toggle:g.menu_action('left')
            toggle.assert_called_once()
            with patch.object(g.settings,'save',return_value=False):g.save_settings()
            self.assertTrue(g.menu.save_failed)
        g.settings_path=None

    def test_pause_configuration_preserves_run_then_resumes_without_jump(self):
        g=self.g;g.state='play';g.lives=2;g.medallions.collect()
        g.handle_pad(PadSnapshot(start_pressed=True))
        g.handle_pad(PadSnapshot(menu_axis=1));g.handle_pad(PadSnapshot(confirm_pressed=True))
        self.assertEqual(g.state,'settings');self.assertEqual(g.menu.origin,'pause')
        before=(g.elapsed,g.hero.x,g.hero.y,g.energy.value,g.lives)
        self.run_events(frames=2)
        self.assertEqual(before,(g.elapsed,g.hero.x,g.hero.y,g.energy.value,g.lives))
        g.handle_pad(PadSnapshot(cancel_pressed=True));self.assertEqual(g.state,'pause')
        g.handle_pad(PadSnapshot(start_pressed=True));self.assertEqual(g.state,'play')
        self.assertEqual(g.medallions.count,1);self.assertFalse(g.pending_jump)
        self.assertTrue(g.menu_gameplay_blocked)

    def test_confirm_is_consumed_until_controller_is_released(self):
        g=self.g;g.handle_pad(PadSnapshot(confirm_pressed=True,jump_pressed=True,jump_held=True))
        self.assertEqual(g.state,'play');self.assertFalse(g.pending_jump)
        self.run_events(pad=PadSnapshot(jump_held=True,activity=True),frames=2)
        self.assertTrue(g.menu_gameplay_blocked);self.assertFalse(g.pending_jump)
        self.assertTrue(g.hero.grounded)
        self.run_events();self.assertFalse(g.menu_gameplay_blocked)
        g.handle_pad(PadSnapshot(jump_pressed=True,jump_held=True));self.assertTrue(g.pending_jump)

    def test_mouse_selects_configuration_and_quit_closes_the_loop(self):
        g=self.g
        for index,expected in ((1,'settings'),(3,'title')):
            if index==3:g.menu_action('back')
            rect=g.menu.rectangles('title')[index]
            position=(round(rect.centerx*1.5),round(rect.centery*1.5))
            self.run_events([pg.event.Event(pg.MOUSEBUTTONDOWN,pos=position,button=1)])
            self.assertEqual(g.state,expected)
        self.assertTrue(g.quit_requested)

    def test_cursor_requires_motion_and_hides_after_three_real_seconds_in_all_menus(self):
        g=self.g
        for page in g.menu.selected:
            g.state=page;g.mouse_last_motion=None;g.update_cursor(100)
            self.assertFalse(pg.mouse.get_visible())
            g.update_cursor(101,moved=True);self.assertTrue(pg.mouse.get_visible())
            g.update_cursor(103.999);self.assertTrue(pg.mouse.get_visible())
            g.update_cursor(104);self.assertFalse(pg.mouse.get_visible())
            g.update_cursor(105,moved=True);g.update_cursor(107,moved=True)
            g.update_cursor(109.999);self.assertTrue(pg.mouse.get_visible())
            g.update_cursor(110);self.assertFalse(pg.mouse.get_visible())

    def test_cursor_cannot_appear_during_play_and_needs_new_motion_after_pause(self):
        g=self.g;g.state='title';g.update_cursor(10,moved=True)
        self.assertTrue(pg.mouse.get_visible())
        g.resume_from_menu();self.assertFalse(pg.mouse.get_visible())
        for page in ('play','win','game_over'):
            g.state=page;g.update_cursor(20,moved=True)
            self.assertFalse(pg.mouse.get_visible());self.assertIsNone(g.mouse_last_motion)
        g.enter_menu('pause');g.update_cursor(21);self.assertFalse(pg.mouse.get_visible())
        g.update_cursor(22,moved=True);self.assertTrue(pg.mouse.get_visible())

    def test_only_actual_mouse_movement_reveals_cursor_not_clicks_or_keyboard(self):
        g=self.g;g.mouse_last_motion=None;pg.mouse.set_visible(False)
        self.run_events([pg.event.Event(pg.MOUSEMOTION,pos=(0,0),rel=(0,0))])
        self.assertFalse(pg.mouse.get_visible())
        self.run_events([pg.event.Event(pg.KEYDOWN,key=pg.K_DOWN)])
        self.assertFalse(pg.mouse.get_visible())
        self.run_events([pg.event.Event(pg.MOUSEBUTTONDOWN,pos=(0,0),button=1)])
        self.assertFalse(pg.mouse.get_visible())
        self.run_events([pg.event.Event(pg.MOUSEMOTION,pos=(100,100),rel=(2,1))])
        self.assertTrue(pg.mouse.get_visible())

    def test_connected_label_is_below_the_hero_on_the_title_screen(self):
        g=self.g;g.pad=PadSnapshot(connected=True)
        with patch.object(g,'text',wraps=g.text) as text:
            g.draw(1,present=False)
        labels=[call for call in text.call_args_list if call.args[0]=='MANETTE CONNECTÉE']
        self.assertEqual(len(labels),1);self.assertEqual(labels[0].args[1],(970,688))

    def test_connection_loss_pauses_before_physics_and_reconnection_does_not_resume(self):
        g=self.g;g.state='play';g.pad=PadSnapshot(connected=True)
        before=(g.elapsed,g.hero.x,g.hero.y,g.energy.value,g.lives)
        self.run_events(pad=PadSnapshot(),frames=2)
        self.assertEqual(g.state,'pause');self.assertTrue(g.controller_lost)
        self.assertEqual(before,(g.elapsed,g.hero.x,g.hero.y,g.energy.value,g.lives))
        self.assertFalse(g.pending_jump);self.assertFalse(g.pending_fire)
        g.handle_pad(PadSnapshot(connected=True));self.assertEqual(g.state,'pause')
        self.assertFalse(g.controller_lost)
        g.handle_pad(PadSnapshot(connected=True,confirm_pressed=True,jump_pressed=True))
        self.assertEqual(g.state,'play');self.assertFalse(g.pending_jump)

    def test_reconnection_clears_warning_consumes_held_start_and_stays_resumed_afterwards(self):
        g=self.g;g.state='play';g.handle_pad(PadSnapshot(connected=True))
        g.handle_pad(PadSnapshot(disconnected=True));self.assertTrue(g.controller_lost)
        g.handle_pad(PadSnapshot(connected=True,start_pressed=True,confirm_pressed=True))
        self.assertEqual(g.state,'pause');self.assertFalse(g.controller_lost)
        with patch.object(g,'text',wraps=g.text) as text:g.draw(1,present=False)
        self.assertFalse(any('Manette déconnectée' in call.args[0] for call in text.call_args_list))
        g.handle_pad(PadSnapshot(connected=True))
        g.handle_pad(PadSnapshot(connected=True,start_pressed=True))
        self.assertEqual(g.state,'play')
        for _ in range(10):g.handle_pad(PadSnapshot(connected=True))
        self.assertEqual(g.state,'play');self.assertFalse(g.controller_lost)

    def test_loss_with_another_pad_connected_ignores_same_frame_confirm(self):
        g=self.g;g.state='play';g.pad=PadSnapshot(connected=True)
        g.pending_jump=g.pending_fire=True
        g.handle_pad(PadSnapshot(connected=True,disconnected=True,confirm_pressed=True,start_pressed=True))
        self.assertEqual(g.state,'pause');self.assertFalse(g.pending_jump);self.assertFalse(g.pending_fire)
        g.draw(1,present=False)

    def test_keyboard_only_play_and_existing_menus_are_unaffected_by_missing_controller(self):
        g=self.g;g.state='play';g.handle_pad(PadSnapshot());self.assertEqual(g.state,'play')
        for page in ('title','settings','save','load','overwrite','pause','win','game_over'):
            g.state=page;g.handle_pad(PadSnapshot(disconnected=True))
            self.assertEqual(g.state,page)

    def test_menu_render_does_not_create_texts_or_advance_gameplay(self):
        g=self.g;g.prepare_rendering();texts=set(g.text_cache)
        before=(g.elapsed,g.lives,g.hero.x,g.hero.y)
        with patch('main.pg.font.SysFont',side_effect=AssertionError('lazy font')):
            for page in g.menu.selected:
                g.state=page
                for index in range(len(g.menu.rectangles(page))):
                    g.menu.selected[page]=index;g.draw(1,present=False)
            g.sound_on=False;g.show_fps=True;g.gamepads.rumble_enabled=False
            g.state='settings';g.draw(1,present=False)
        self.assertEqual(texts,set(g.text_cache));self.assertEqual(before,(g.elapsed,g.lives,g.hero.x,g.hero.y))


if __name__=='__main__':unittest.main()
