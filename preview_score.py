"""Capture the score HUD and summaries using the real renderer."""
import json
from pathlib import Path
import tempfile
import pygame as pg
from main import Game,ROOT


def preview():
    with tempfile.TemporaryDirectory() as folder:
        game=Game(False,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        try:
            game.settings.language='fr';game.sound_on=False;game.gamepads.rumble_enabled=False
            game.new_game();game.state='play';game.award_points(2340)
            game.cam=game.prev_cam=1200;game.hero.x=1700
            game.draw(1);pg.image.save(game.capture(),ROOT/'output'/'score-hud.png')
            game.complete_level();game.draw(1)
            pg.image.save(game.capture(),ROOT/'output'/'score-victory.png')
            game.state='game_over';game.lives=0;game.deaths=3;game.draw(1)
            pg.image.save(game.capture(),ROOT/'output'/'score-game-over.png')
            report=dict(gpu=game.native_canvas.gpu,score=game.score,level_score=game.level_score,bonus=1300)
            (ROOT/'output'/'score-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:game.close()


if __name__=='__main__':preview()
