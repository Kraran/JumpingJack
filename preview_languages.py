"""Native language menu/HUD review with temporary preferences and saves."""
import argparse
import json
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,ROOT
from localization import CODES,LANGUAGES
from savegame import capture


def preview(native=False):
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        try:
            game.start_level(3);game.lives=2;game.medallions.collect(1);game.taken={0,2,5};game.saves.write(0,capture(game))
            records=[]
            for code,name in LANGUAGES:
                game.enter_menu('settings');game.set_language(code);game.menu.selected['settings']=5
                before=game.native_canvas.uploads;game.draw(1)
                if code in ('en','ru'):pg.image.save(game.capture(),ROOT/'output'/f'language-settings-{code}.png')
                game.enter_menu('languages');game.menu.selected['languages']=CODES.index(code);game.draw(1)
                if code in ('fr','ru'):pg.image.save(game.capture(),ROOT/'output'/f'languages-{code}.png')
                game.enter_menu('load');game.draw(1)
                if code=='ru':pg.image.save(game.capture(),ROOT/'output'/'language-saves-ru.png')
                game.state='play';game.draw(1)
                if code=='ru':pg.image.save(game.capture(),ROOT/'output'/'language-game-ru.png')
                records.append({'language':code,'native_name':name,'new_texture_uploads':game.native_canvas.uploads-before})
            (ROOT/'output'/'languages-validation.json').write_text(json.dumps({'gpu':game.native_canvas.gpu,
                'renderer':game.presentation.renderer,'languages':records,'lives':game.lives,'elapsed':game.elapsed,
                'scope':'All languages: settings, native flags/names, saved summaries and temple HUD; temporary files only.'},ensure_ascii=False,indent=2),encoding='utf-8')
        finally:game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
