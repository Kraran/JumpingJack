"""Real staged beetle contacts: grounded, airborne and the final life."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch
import pygame as pg
from main import Game,Hero,ROOT,STEP
from hero_death import BEETLE_DURATION,FRAMES
from beetle_death import POSE_TIME


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        g=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'hero-beetle-death-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            sections=[];uploads=0;seen=set()
            for name,air,lives,face in (('ground',False,3,1),('air',True,3,-1),('game-over',False,1,-1)):
                g.new_game();g.state='play';g.lives=lives
                enemy=g.beetle_motions[0]
                enemy.x=enemy.px=3000. if air else 1600.;enemy.y=enemy.py=200. if air else 593.
                g.hero=Hero(enemy.x+25,enemy.y+27);g.hero.grounded=not air;g.hero.face=face
                g.cam=g.prev_cam=g.hero.x-512
                with patch.object(enemy,'update'):g.update(STEP,0,False,False)
                assert g.hero_death.active and g.hero_death.kind=='beetle'
                for frame in range(210):
                    pg.event.pump()
                    before=g.native_canvas.uploads
                    for _ in range(2):
                        if g.state=='play':g.update(STEP,0,False,False)
                        g.time+=STEP
                    active=g.hero_death.active
                    g.draw(1)
                    if active:
                        uploads+=g.native_canvas.uploads-before
                        seen.add((face,min(FRAMES-1,int(g.hero_death.elapsed/POSE_TIME*(FRAMES-1)))))
                    image=g.capture()
                    if name=='ground' and frame in (12,43):
                        label='electrocution' if frame==12 else 'collapse'
                        pg.image.save(image,ROOT/'output'/f'hero-beetle-{label}.png')
                    if name=='air' and frame==25:pg.image.save(image,ROOT/'output'/'hero-beetle-air.png')
                    if name=='game-over' and frame==100:pg.image.save(image,ROOT/'output'/'hero-beetle-game-over.png')
                    writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
                sections.append(dict(cause=name,lives=g.lives,deaths=g.deaths,state=g.state))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            data=dict(gpu=g.native_canvas.gpu,sequence_seconds=BEETLE_DURATION,poses_per_facing=FRAMES,
                      observed_poses=len(seen),new_death_texture_uploads=uploads,sections=sections)
            (ROOT/'output'/'hero-beetle-death-validation.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
            print(data)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
