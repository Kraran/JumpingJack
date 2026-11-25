"""Capture actual startup stages; never sleeps to fake loading progress."""
import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pygame as pg
from main import Game,ROOT
from loading import LoadingScreen


def preview(native=False):
    stages=[];original=LoadingScreen.show
    def observe(loader,canvas,screen,progress,label):
        original(loader,canvas,screen,progress,label)
        stages.append({'progress':loader.progress,'label':label})
        if loader.enabled:
            if progress in (0,.40,.86,1.):
                name={0:'opening',.40:'hero',.86:'textures',1.:'ready'}[progress]
                pg.image.save(canvas.capture(),ROOT/'output'/f'loading-{name}.png')
    with tempfile.TemporaryDirectory() as directory:
        with patch.object(LoadingScreen,'show',observe):
            game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        try:
            game.draw(1);pg.image.save(game.capture(),ROOT/'output'/'loading-menu.png')
            (ROOT/'output'/'loading-validation.json').write_text(json.dumps({'gpu':game.native_canvas.gpu,
                'renderer':game.presentation.renderer,'stages':stages,'state_after_loading':game.state,
                'elapsed':game.elapsed,'loading_active':game.loading.active,
                'scope':'Actual startup stages and native GPU presentation, without artificial delay.'},ensure_ascii=False,indent=2),encoding='utf-8')
        finally:game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
