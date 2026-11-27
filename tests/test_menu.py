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

    def test_holding_horizontal_changes_volume_only_once_until_released(self):
        g=self.g;g.enter_menu('settings');g.menu.selected['settings']=1
        for now in (0,.1,.5,1.):
            g.time=now;g.handle_pad(PadSnapshot(axis=-1))
            self.assertEqual(g.settings.sound_volume,90)
        g.handle_pad(PadSnapshot());g.handle_pad(PadSnapshot(axis=-1))
        self.assertEqual(g.settings.sound_volume,80)

    def test_options_apply_and_save_sound_vibration_fps_and_display(self):
        g=self.g;g.enter_menu('settings')
        with tempfile.TemporaryDirectory() as directory:
            g.settings_path=Path(directory)/'settings.json'
            for index in (1,2,3):
                g.menu.selected['settings']=index;g.menu_action('activate' if index==1 else 'right')
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

    def test_audio_volumes_apply_immediately_clamp_and_persist_independently(self):
        g=self.g;g.enter_menu('settings')
        with tempfile.TemporaryDirectory() as directory:
            g.settings_path=Path(directory)/'settings.json'
            g.menu.selected['settings']=1;g.menu_action('left')
            self.assertEqual(g.settings.sound_volume,90)
            self.assertAlmostEqual(g.sounds['jump'].get_volume(),.9,delta=.01)
            g.menu.selected['settings']=6;g.menu_action('left')
            self.assertEqual(g.settings.music_volume,90)
            for _ in range(12):g.menu_action('left')
            self.assertEqual(g.settings.music_volume,0);self.assertFalse(g.settings.music)
            self.assertEqual(g.settings.sound_volume,90);self.assertTrue(g.sound_on)
            g.menu_action('right')
            self.assertEqual(g.settings.music_volume,10);self.assertTrue(g.settings.music)
            loaded=Settings.load(g.settings_path)
            self.assertEqual((loaded.sound_volume,loaded.music_volume),(90,10))
            g.adjust_volume('music',-1);g.toggle_music()
            self.assertEqual(g.settings.music_volume,100);self.assertTrue(g.settings.music)
            g.menu.selected['settings']=1
            for _ in range(10):g.menu_action('left')
            self.assertFalse(g.sound_on)
            g.toggle_sound()
            self.assertTrue(g.sound_on);self.assertEqual(g.settings.sound_volume,100)
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

    def test_escape_resume_blocks_held_keyboard_or_stick_until_release(self):
        class Keys:
            def __init__(self,*held):self.held=set(held)
            def __getitem__(self,key):return key in self.held
            def __iter__(self):return iter((bool(self.held),))
        g=self.g
        for key,pad,air in ((pg.K_SPACE,PadSnapshot(),False),(pg.K_RIGHT,PadSnapshot(),False),
                            (None,PadSnapshot(axis=1,activity=True),False),(pg.K_SPACE,PadSnapshot(),True)):
            with self.subTest(key=key,stick=pad.axis,air=air):
                g.new_game();g.state='play'
                if air:
                    g.hero.y=g.hero.py=300;g.hero.grounded=False;g.hero.vy=105;g.hero.floating=True
                g.enter_menu('pause')
                g.pending_jump=g.pending_drop=g.pending_fire=True
                keys=Keys() if key is None else Keys(key)
                with patch('main.pg.key.get_pressed',return_value=keys),\
                     patch.object(g,'resume_from_menu',wraps=g.resume_from_menu) as resume,\
                     patch.object(g,'update',wraps=g.update) as update:
                    self.run_events([pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE)],pad=pad)
                    resume.assert_called_once_with()
                    self.assertEqual(g.state,'play');self.assertTrue(g.menu_gameplay_blocked)
                    self.assertFalse(g.pending_jump or g.pending_drop or g.pending_fire)
                    if not air:self.assertEqual((g.hero.x,g.hero.y),(160,620))
                    # Force a physics step while the controls remain held.
                    g.acc=2/120;self.run_events(pad=pad)
                    self.assertTrue(update.called)
                    self.assertFalse(g.hero.floating)
                    for call in update.call_args_list:
                        self.assertEqual(call.args[1:6],(0,False,False,False,False))
                with patch('main.pg.key.get_pressed',return_value=Keys()):
                    self.run_events()
                self.assertFalse(g.menu_gameplay_blocked)
                with patch('main.pg.key.get_pressed',return_value=Keys(pg.K_RIGHT)):
                    g.acc=2/120;self.run_events()
                self.assertGreater(g.hero.x,160)

    def test_mouse_selects_configuration_and_quit_closes_the_loop(self):
        g=self.g
        for index,expected in ((1,'settings'),(3,'title')):
            if index==3:g.menu_action('back')
            rect=g.menu.rectangles('title')[index]
            position=(round(rect.centerx*1.5),round(rect.centery*1.5))
            self.run_events([pg.event.Event(pg.MOUSEBUTTONDOWN,pos=position,button=1)])
            self.assertEqual(g.state,expected)
        self.assertTrue(g.quit_requested)

    def test_clicking_each_volume_gauge_sets_exact_position_and_saves(self):
        g=self.g;g.enter_menu('settings')
        with tempfile.TemporaryDirectory() as directory:
            g.settings_path=Path(directory)/'settings.json'
            for index,kind in ((1,'sound'),(6,'music')):
                gauge=g.menu.volume_gauge(index)
                other='music' if kind=='sound' else 'sound'
                previous=getattr(g.settings,other+'_volume')
                for percent in (25,0,100,50,75):
                    with self.subTest(kind=kind,percent=percent):
                        position=(round((gauge.x+gauge.width*percent/100)*1.5),round(gauge.centery*1.5))
                        self.run_events([pg.event.Event(pg.MOUSEBUTTONDOWN,pos=position,button=1)])
                        self.assertEqual(getattr(g.settings,kind+'_volume'),percent)
                        self.assertEqual(getattr(Settings.load(g.settings_path),kind+'_volume'),percent)
                        self.assertEqual(getattr(g.settings,other+'_volume'),previous)
                        self.assertEqual(g.sound_on if kind=='sound' else g.settings.music,percent>0)
                        if kind=='sound':self.assertAlmostEqual(g.sounds['jump'].get_volume(),percent/100,delta=.01)
                        self.assertEqual(g.state,'settings')
        g.settings_path=None

    def test_gauge_hover_and_right_click_do_not_change_volume(self):
        g=self.g;g.enter_menu('settings');g.set_volume('sound',40)
        gauge=g.menu.volume_gauge(1)
        position=(round(gauge.centerx*1.5),round(gauge.centery*1.5))
        for event in (pg.event.Event(pg.MOUSEMOTION,pos=position,rel=(1,0)),
                      pg.event.Event(pg.MOUSEBUTTONDOWN,pos=position,button=3)):
            self.run_events([event]);self.assertEqual(g.settings.sound_volume,40)

    def test_volume_drag_tracks_original_gauge_clamps_and_saves_on_release(self):
        g=self.g
        with tempfile.TemporaryDirectory() as directory:
            g.settings_path=Path(directory)/'settings.json'
            for index,kind in ((1,'sound'),(6,'music')):
                g.enter_menu('settings');gauge=g.menu.volume_gauge(index)
                def position(x,y=gauge.centery):return (round(x*1.5),round(y*1.5))
                self.run_events([pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=position(gauge.x+24))])
                self.assertEqual(g.menu.volume_drag,index)
                self.run_events([pg.event.Event(pg.MOUSEMOTION,pos=position(gauge.right+50,280),rel=(10,0),buttons=(1,0,0))])
                self.assertEqual(getattr(g.settings,kind+'_volume'),100)
                self.assertEqual(g.menu.selected['settings'],index)
                self.run_events([pg.event.Event(pg.MOUSEMOTION,pos=position(gauge.left-50),rel=(-10,0),buttons=(1,0,0))])
                self.assertEqual(getattr(g.settings,kind+'_volume'),0)
                self.assertEqual(getattr(Settings.load(g.settings_path),kind+'_volume'),25)
                self.run_events([pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=position(gauge.centerx))])
                self.assertIsNone(g.menu.volume_drag)
                self.assertEqual(getattr(Settings.load(g.settings_path),kind+'_volume'),50)
                self.run_events([pg.event.Event(pg.MOUSEMOTION,pos=position(gauge.right),rel=(10,0),buttons=(0,0,0))])
                self.assertEqual(getattr(g.settings,kind+'_volume'),50)
        g.settings_path=None

    def test_focus_loss_stops_volume_drag(self):
        g=self.g;g.enter_menu('settings');gauge=g.menu.volume_gauge(1)
        g.menu.click_volume(g,gauge.center)
        self.assertIsNotNone(g.menu.volume_drag)
        self.run_events([pg.event.Event(pg.WINDOWFOCUSLOST)])
        self.assertIsNone(g.menu.volume_drag)

    def test_pause_music_is_thirty_percent_quieter_without_changing_preference(self):
        g=self.g;g.settings.music_volume=80
        for origin in ('title','pause'):
            g.menu.origin=origin
            for page in ('title','pause','save','overwrite','settings','controls','languages','load'):
                with self.subTest(origin=origin,page=page):
                    g.state=page
                    paused=page in ('pause','save','overwrite') or origin=='pause' and page in ('settings','controls','languages')
                    with patch.object(g.menu_music,'update') as update:g.sync_menu_music()
                    self.assertAlmostEqual(update.call_args.kwargs['volume'],.8*(.7 if paused else 1.))
                    self.assertEqual(g.settings.music_volume,80)

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
