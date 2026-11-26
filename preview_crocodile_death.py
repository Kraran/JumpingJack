"""Render real crocodile collisions, both orientations and the final life."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP
from hero_death import CAPTURE,FRAMES,DURATION


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        g=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'hero-crocodile-death-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            sections=[];uploads=0;poses=set()
            for level,face,lives in ((1,-1,3),(2,1,3),(1,1,1)):
                g.new_game();g.start_level(level);g.state='play';g.lives=lives
                enemy=g.crocodiles[0];enemy.facing=enemy.previous_facing=face
                g.hero=Hero(enemy.x+face*60,enemy.y);g.hero.grounded=True
                g.cam=g.prev_cam=max(0,min(g.world_length-1280,enemy.x-640))
                g.update(STEP,0,False,False)
                assert g.hero_death.active
                for frame in range(180):
                    pg.event.pump()
                    for _ in range(2):
                        if g.state=='play':g.update(STEP,0,False,False)
                        g.time+=STEP
                    before=g.native_canvas.uploads;active=g.hero_death.active
                    g.draw(1)
                    if active:
                        uploads+=g.native_canvas.uploads-before
                        t=g.hero_death.elapsed
                        if t>=CAPTURE:poses.add((face,min(FRAMES-1,int((t-CAPTURE)/(DURATION-CAPTURE)*FRAMES))))
                    image=g.capture()
                    if level==1 and face==-1 and frame in (24,52):
                        pg.image.save(image,ROOT/'output'/('hero-crocodile-capture.png' if frame==24 else 'hero-crocodile-devoured.png'))
                    writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
                sections.append(dict(level=level,facing=face,initial_lives=lives,lives=g.lives,deaths=g.deaths,state=g.state))
            writer.stdin.close();error=writer.stderr.read().decode();result=writer.wait();writer=None
            if result:raise RuntimeError(error)
            report=dict(gpu=g.native_canvas.gpu,sequence_seconds=DURATION,authored_poses=16,cached_poses_per_direction=FRAMES,
                        observed_poses=len(poses),new_sequence_texture_uploads=uploads,sections=sections)
            (ROOT/'output'/'hero-crocodile-death-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
