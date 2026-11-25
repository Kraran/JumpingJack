import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch
from main import Game
from savegame import capture
from localization import CODES,translate


class VictoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def test_every_level_renders_its_actual_results_without_changing_the_game(self):
        g=self.g
        titles=('LE SEUIL EST FRANCHI','LE TEMPLE EST ATTEINT','LE SANCTUAIRE EST ATTEINT','LE SOMMET EST ATTEINT')
        for level_id,title in enumerate(titles,1):
            with self.subTest(level=level_id):
                g.start_level(level_id);g.state='win'
                g.taken={0,1,2};g.elapsed=125.9;g.deaths=2
                before=json.loads(json.dumps(capture(g)))
                summary=f'3 / {len(g.gems)} éclats solaires   ·   02:05   ·   2 morts'
                with patch.object(g,'text',wraps=g.text) as text:
                    g.draw(.5,present=False)
                calls=[call.args[0] for call in text.call_args_list]
                self.assertEqual(calls.count(summary),1)
                self.assertIn(title,calls)
                self.assertIn('Entrée, Start ou A pour rejouer' if level_id==4 else 'Entrée, Start ou A pour continuer',calls)
                self.assertEqual(json.loads(json.dumps(capture(g))),before)

    def test_results_preserve_numbers_in_every_supported_language(self):
        source='3 / 96 éclats solaires   ·   62:05   ·   2 morts'
        for language in CODES:
            with self.subTest(language=language):
                result=translate(source,language)
                for number in ('3 / 96','62:05','2'):self.assertIn(number,result)
                if language!='fr':
                    self.assertNotIn('éclats solaires',result);self.assertNotIn('morts',result)
