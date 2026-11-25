"""Real walk into the ruined temple at the end of the desert."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP,VIEW_W
from desert_level import LENGTH,TEMPLE_FINISH
from terrain import sand_height


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            game.start_level(2);game.state='play';game.sound_on=False;game.invuln=100
            game.hero=Hero(14035,sand_height(14035));game.hero.grounded=True
            game.hero_animation.reset();game.cam=game.prev_cam=LENGTH-VIEW_W
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                     '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                     '-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'temple-entry-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0;observations=[]
            for frame in range(210):
                pg.event.pump()
                for _ in range(2):
                    game.time+=STEP
                    if game.state=='play':game.update(STEP,1 if frame>=45 else 0,False,False)
                game.cam=game.prev_cam=LENGTH-VIEW_W
                protection=game.invuln;game.invuln=0;before=game.native_canvas.uploads
                try:game.draw(1)
                finally:game.invuln=protection
                if game.state=='play':uploads+=game.native_canvas.uploads-before
                screen=game.capture()
                for at,name in ((20,'exterior'),(80,'entering'),(104,'inside'),(135,'complete')):
                    if frame==at:
                        pg.image.save(screen,ROOT/'output'/f'temple-{name}.png')
                        observations.append({'frame':frame,'hero':[game.hero.x,game.hero.y],'state':game.state})
                writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(screen,(960,540)),'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert game.state=='win' and game.hero.x>=TEMPLE_FINISH and game.lives==3
            (ROOT/'output'/'temple-validation.json').write_text(json.dumps({
                'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                'new_texture_uploads_during_gameplay':uploads,'lives':game.lives,
                'finish_x':TEMPLE_FINISH,'observations':observations,
                'scope':'Real physics and fixed final camera; enemies temporarily prevented from attacking.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
