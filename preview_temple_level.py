"""Controlled native shots of level 03 with real physics and collectibles."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP,VIEW_W
import temple_level as temple


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            game.start_level(3);game.state='play';game.sound_on=False;game.invuln=100
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                     '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'temple-level-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0;shots=[]
            for name,x,y in (('hall',550,620),('galleries',5550,620),('medallion',12960,455),('sanctuary',13900,620)):
                game.hero=Hero(x,y);game.hero.grounded=True;game.hero_animation.reset();game.rest.reset()
                for frame in range(400 if name=='sanctuary' else 140):
                    pg.event.pump()
                    for step in range(2):
                        game.time+=STEP
                        if game.state=='play':game.update(STEP,0 if name=='medallion' else 1,False,name=='medallion' and frame==20 and step==0)
                    game.cam=game.prev_cam=max(0,min(temple.LENGTH-VIEW_W,game.hero.x-500))
                    before=game.native_canvas.uploads;protection=game.invuln;game.invuln=0
                    try:game.draw(1)
                    finally:game.invuln=protection
                    if game.state=='play':uploads+=game.native_canvas.uploads-before
                    image=game.capture()
                    if frame==70:
                        pg.image.save(image,ROOT/'output'/f'temple-level-{name}.png')
                        shots.append({'shot':name,'hero':[game.hero.x,game.hero.y],'medallions':game.medallions.count})
                    writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert game.state=='win' and game.lives==3 and 3 in game.medallions.claimed_levels
            (ROOT/'output'/'temple-level-validation.json').write_text(json.dumps({'gpu':game.native_canvas.gpu,
                'renderer':game.presentation.renderer,'new_texture_uploads_during_gameplay':uploads,
                'length':temple.LENGTH,'supports':len(game.platforms),'crystals':len(game.gems),'shots':shots,
                'scope':'Controlled cuts, real physics and pickups; temporary protection from enemies.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
