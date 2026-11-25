import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame as pg
from localization import CODES,LANGUAGES,CORE,CORE_KEYS,SENTENCES,SENTENCE_KEYS,translate,LOADING_CATEGORIES
from settings import Settings
from main import Game
from savegame import capture
from gamepad import PadSnapshot
from loading import LoadingScreen


class CatalogTests(unittest.TestCase):
    def test_all_twenty_languages_have_complete_catalogs(self):
        self.assertEqual(len(CODES),20)
        self.assertNotIn('uk',CODES)
        for code in CODES:
            self.assertEqual(set(CORE[code]),set(CORE_KEYS));self.assertEqual(set(SENTENCES[code]),set(SENTENCE_KEYS))
            self.assertTrue(all(CORE[code].values()));self.assertTrue(all(SENTENCES[code].values()))
            if code!='fr':
                for source in ('Jouer','Langue','Manette connectée','ÉNERGIE INSUFFISANTE',*LOADING_CATEGORIES):
                    self.assertNotEqual(translate(source,code),source)

    def test_cyrillic_and_latin_saved_summaries_keep_numbers_and_translate_labels(self):
        header='Emplacement 2 · Niveau 03 · 4 vies'
        detail='Parcours 90 % · Éclats 12/79 · Médaillons 2/3 · Énergie 70 % · Temps 04:21'
        for code in CODES[1:]:
            result=translate(header,code)+' '+translate(detail,code)
            for number in ('03','90','12/79','2/3','70','04:21'):self.assertIn(number,result)
            self.assertNotIn('Emplacement',result);self.assertNotIn('Énergie',result)
        self.assertIn('Ячейка',translate(header,'ru'));self.assertIn('ХРАМ',translate('NIVEAU 03  /  LE TEMPLE','ru'))

    @patch('settings.detect_system_language',return_value='fr')
    def test_settings_accept_only_supported_language_codes_and_keep_old_files_compatible(self,detect):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            for value in ('ru','en','uk','invalid',None,False,[],{}):
                path.write_text(json.dumps({'language':value,'sound':False}),encoding='utf-8')
                settings=Settings.load(path)
                self.assertEqual(settings.language,value if value in ('ru','en') else 'en');self.assertFalse(settings.sound)
            choices=Settings(language='fi');self.assertTrue(choices.save(path));self.assertEqual(Settings.load(path),choices)
            path.write_text('{"sound": false}',encoding='utf-8');self.assertEqual(Settings.load(path).language,'fr')


class LanguageMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        g=self.g;g.settings_path=None;g.new_game();g.state='title';g.pad=PadSnapshot()
        g.set_language('fr');g.menu.selected['settings']=5

    def test_keyboard_mouse_and_controller_choose_language_and_return_to_settings(self):
        g=self.g;g.enter_menu('settings');g.menu_action('activate')
        self.assertEqual(g.state,'languages');self.assertEqual(g.menu.selected['languages'],0)
        g.menu_key(pg.K_RIGHT);self.assertEqual(g.menu.selected['languages'],1)
        g.handle_pad(PadSnapshot(confirm_pressed=True));self.assertEqual(g.settings.language,'en')
        target=CODES.index('ru');g.menu.pointer('languages',g.menu.rectangles('languages')[target].center)
        g.menu_action('activate');self.assertEqual(g.settings.language,'ru')
        g.menu_action('back');self.assertEqual(g.state,'settings')
        self.assertEqual(g.menu.values(g)[5],'Русский')

    def test_language_change_persists_without_changing_the_paused_game_or_save_payload(self):
        g=self.g;g.start_level(3);g.lives=2;g.medallions.collect(1);g.energy.value=41
        g.enter_menu('pause');g.menu.origin='pause';g.enter_menu('settings')
        before=json.loads(json.dumps(capture(g)))
        with tempfile.TemporaryDirectory() as directory:
            g.settings_path=Path(directory)/'settings.json';g.set_language('fi')
            self.assertEqual(Settings.load(g.settings_path).language,'fi')
        g.settings_path=None
        self.assertEqual(json.loads(json.dumps(capture(g))),before);self.assertEqual(g.state,'settings')
        g.menu_action('back');self.assertEqual(g.state,'pause')

    def test_all_flags_and_native_names_render_and_texts_are_warmed_for_each_language(self):
        g=self.g
        for code,name in LANGUAGES:
            g.set_language(code);g.enter_menu('languages');g.menu.selected['languages']=CODES.index(code)
            for character in name:
                if not character.isspace():self.assertIsNotNone(g.font(19).metrics(character)[0])
            alphabet=set(''.join(CORE[code].values())+''.join(SENTENCES[code].values()))
            for character in alphabet:
                if character.isalpha():self.assertIsNotNone(g.font(17).metrics(character)[0],(code,character))
            image=g.menu.flags.atlas.subsurface(g.menu.flags.areas[code])
            self.assertEqual(image.get_size(),(48,30));self.assertGreater(len(set(pg.image.tobytes(image,'RGB'))),2)
            before=set(g.text_cache)
            with patch('main.pg.font.SysFont',side_effect=AssertionError('lazy font after language change')):
                g.draw(1,present=False)
                g.state='play';g.draw(1,present=False)
            self.assertEqual(set(g.text_cache),before)

    def test_loading_screen_uses_the_saved_language(self):
        loading=LoadingScreen(enabled=False,language='ru')
        self.assertEqual(loading.language,'ru')
        self.assertEqual(translate('Préparation de votre aventure',loading.language),'Подготовка приключения')

    def test_nordic_languages_have_distinct_flags_and_fit_the_language_grid(self):
        g=self.g;expected={'sv','da','nb','fi','is'}
        self.assertTrue(expected<=set(CODES))
        rectangles=g.menu.rectangles('languages')
        for index,rect in enumerate(rectangles):
            self.assertLessEqual(rect.bottom,650)
            for other in rectangles[index+1:]:self.assertFalse(rect.colliderect(other))
        flags=[]
        for code in expected:
            image=g.menu.flags.atlas.subsurface(g.menu.flags.areas[code])
            flags.append(pg.image.tobytes(image,'RGB'))
            self.assertNotEqual(translate('Configuration',code),'Configuration')
            self.assertNotIn('morts',translate('1 / 79 éclats solaires   ·   04:21   ·   2 morts',code))
            g.set_language(code);g.enter_menu('languages');g.draw(1,present=False)
        self.assertEqual(len(set(flags)),5)

    def test_settings_arrows_cycle_languages_and_standard_player_texts_have_translations(self):
        g=self.g;g.enter_menu('settings');g.menu_action('right');self.assertEqual(g.settings.language,'en')
        g.menu_action('left');self.assertEqual(g.settings.language,'fr')
        sources=set()
        with patch.object(g,'text',wraps=g.text) as text:
            for page in g.menu.selected:
                g.enter_menu(page);g.draw(1,present=False)
            g.state='play';g.extra_life_notice=1;g.energy.warning=1;g.draw(1,present=False)
            g.state='pause';g.controller_lost=True;g.draw(1,present=False)
            sources={call.args[0] for call in text.call_args_list}
        allowed={name for code,name in LANGUAGES}|{'JUMPING JACK','FULL HD','FPS','PAUSE','Pause','Start','F','RT / B','← → / Q D'}
        for source in sources:
            if source in allowed or not any(character.isalpha() for character in source):continue
            self.assertNotEqual(translate(source,'en'),source,source)
