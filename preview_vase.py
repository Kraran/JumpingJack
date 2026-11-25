"""Demonstrate solid pottery and an actual solar-ray shatter in the temple."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        g=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            g.start_level(3);g.state='play';g.sound_on=False;g.invuln=100
            g.scorpions=[];g.beetle_motions=[]
            g.hero=Hero(680,620);g.hero.grounded=True
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'egyptian-vase-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0;blocked=False
            for frame in range(240):
                pg.event.pump()
                for step in range(2):
                    g.time+=STEP;g.update(STEP,1 if frame<65 or frame>125 else 0,False,False,fire=frame==85 and step==0)
                if frame==64:blocked=abs(g.hero.x-(g.vases[0].x-15))<.1
                g.cam=g.prev_cam=300;before=g.native_canvas.uploads;protection=g.invuln;g.invuln=0
                try:g.draw(1)
                finally:g.invuln=protection
                uploads+=g.native_canvas.uploads-before;image=g.capture()
                if frame in (60,103):pg.image.save(image,ROOT/'output'/('egyptian-vase-game.png' if frame==60 else 'egyptian-vase-shattering.png'))
                writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(1280,720)),'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert blocked and g.vases[0].broken and g.hero.x>g.vases[0].x+g.vases[0].w and g.lives==3
            (ROOT/'output'/'egyptian-vase-validation.json').write_text(json.dumps({'gpu':g.native_canvas.gpu,
                'renderer':g.presentation.renderer,'new_texture_uploads':uploads,'blocked_before_ray':blocked,
                'broken':g.vases[0].broken,'passed_after_ray':True,'lives':g.lives},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
