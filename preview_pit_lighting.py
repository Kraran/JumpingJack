"""Show light at the lip and darkness at depth in real level openings."""
import os
import sys
gpu='--gpu' in sys.argv
if not gpu:
    os.environ['SDL_VIDEODRIVER']='dummy'
    os.environ['SDL_AUDIODRIVER']='dummy'
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT


with tempfile.TemporaryDirectory() as folder:
    game=Game(not gpu,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
    try:
        for stage in (1,3):
            game.new_game();game.start_level(stage);game.state='play'
            a,b=game.pit_regions[0];center=(a+b)/2
            game.cam=game.prev_cam=center-640
            game.hero=Hero(center,600);game.invuln=100
            before=game.native_canvas.uploads
            game.draw(1,present=False)
            assert game.native_canvas.uploads==before
            pg.image.save(game.capture(),ROOT/'output'/f'pit-stone-level{stage}.png')
        print(dict(gpu=game.native_canvas.gpu,new_texture_uploads=0))
    finally:game.close()
