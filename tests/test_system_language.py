import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from settings import Settings,detect_system_language,system_locale
from main import Game


class SystemLanguageTests(unittest.TestCase):
    def test_supported_regions_scripts_and_norwegian_alias(self):
        cases={'fr-FR':'fr','fr_CA.UTF-8':'fr','English_United States':'en','pt-BR':'pt',
               'es_419':'es','de-DE':'de','sr-Latn-RS':'sr','ru_RU':'ru','no_NO':'nb',
               'nb-NO':'nb','sv-SE':'sv','da_DK':'da','fi-FI':'fi','is_IS':'is'}
        for name,expected in cases.items():
            with self.subTest(locale=name),patch('settings.system_locale',return_value=name):
                self.assertEqual(detect_system_language(),expected)

    def test_unsupported_or_unavailable_system_languages_fall_back_to_english(self):
        for name in ('ja_JP','zh-Hans-CN','uk-UA','',None,'not_a_locale'):
            with patch('settings.system_locale',return_value=name):self.assertEqual(detect_system_language(),'en')
        with patch('settings.system_locale',side_effect=OSError('unavailable')):
            self.assertEqual(detect_system_language(),'en')

    def test_windows_display_language_has_priority_over_environment(self):
        native=MagicMock();native.kernel32.GetUserDefaultUILanguage.return_value=0x040B
        with patch('settings.os.name','nt'),patch('settings.ctypes.windll',native,create=True),\
             patch('settings.locale.windows_locale',{0x040B:'fi_FI'},create=True),\
             patch.dict(os.environ,{'LANG':'ja_JP','LANGUAGE':'de_DE'}):
            self.assertEqual(system_locale(),'fi_FI');self.assertEqual(detect_system_language(),'fi')

    def test_non_windows_locale_environment_is_normalized(self):
        with patch('settings.os.name','posix'),patch.dict(os.environ,{'LANGUAGE':'sv_SE:en','LC_ALL':'de_DE'},clear=True):
            self.assertEqual(detect_system_language(),'sv')

    def test_saved_selection_overrides_system_and_legacy_files_keep_other_options(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json';Settings(sound=False,language='de').save(path)
            with patch('settings.detect_system_language',side_effect=AssertionError('saved choice ignored')):
                self.assertEqual(Settings.load(path).language,'de')
            path.write_text('{"sound": false, "rumble": false}',encoding='utf-8')
            with patch('settings.detect_system_language',return_value='da'):
                loaded=Settings.load(path)
            self.assertEqual(loaded.language,'da');self.assertFalse(loaded.sound);self.assertFalse(loaded.rumble)
            path.write_text('{"language": "uk", "sound": false}',encoding='utf-8')
            self.assertEqual(Settings.load(path).language,'en')

    def test_first_launch_saves_detection_before_loading_and_never_redetects_next_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            with patch('settings.detect_system_language',return_value='fi') as detect:
                game=Game(True,settings_path=path)
            try:
                self.assertEqual(game.settings.language,'fi');self.assertEqual(game.loading.language,'fi')
                self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['language'],'fi')
                detect.assert_called_once()
            finally:game.close()
            with patch('settings.detect_system_language',side_effect=AssertionError('redetected')):
                game=Game(True,settings_path=path)
            try:self.assertEqual(game.settings.language,'fi')
            finally:game.close()

    def test_headless_defaults_do_not_probe_the_host_system(self):
        with patch('settings.detect_system_language',side_effect=AssertionError('host locale used')):
            self.assertEqual(Settings.load(None),Settings())
