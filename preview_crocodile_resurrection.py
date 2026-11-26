"""Reproduce the crocodile/death/resurrection handoff at 75 Hz."""
import argparse
import json
from pathlib import Path
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP


def preview(label):
    with tempfile.TemporaryDirectory() as folder:
        game=Game(False,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        try:
            game.sound_on=False;game.gamepads.rumble_enabled=False
            game.new_game();game.state='play'
            enemy=game.crocodiles[0]
            enemy.state=enemy.previous_state='lunge'
            enemy.facing=enemy.previous_facing=-1
            game.hero=Hero(enemy.x+40,enemy.y);game.hero.grounded=True
            game.cam=game.prev_cam=enemy.x-450
            game.update(STEP,0,False,False)
            while game.hero_death.active:game.update(STEP,0,False,False)
            # Compare the actor alone, without the growing screen-space emblem.
            images=[]
            for alpha in (0,.25,.5,.75,1):
                game.native_canvas.begin();game.draw_crocodiles(game.cam,alpha)
                images.append(pg.image.tobytes(game.capture(),'RGB'))
            game.draw(1);pg.image.save(game.capture(),ROOT/'output'/f'crocodile-revival-{label}.png')
            accumulator=0.
            for _ in range(75):
                pg.event.pump();accumulator+=1/75
                while accumulator>=STEP:
                    game.update(STEP,0,False,False);accumulator-=STEP
                game.draw(accumulator/STEP)
            report=dict(gpu=game.native_canvas.gpu,distinct_crocodile_frames=len(set(images)),
                        lives=game.lives,deaths=game.deaths,spawned=game.resurrection.spawned,
                        crocodile_state=enemy.state,crocodile_facing=enemy.facing)
            (ROOT/'output'/f'crocodile-revival-{label}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='after')
    preview(parser.parse_args().label)
