"""Native HUD emblem zoom and flash, including crocodile and tower respawns."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP
import tower_level as tower
from resurrection import DURATION,REAPPEAR


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        g=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'hero-resurrection-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            sections=[];uploads=0
            for name,level,frames in (('fall',1,150),('crocodile',1,270),('tower',4,150)):
                g.new_game();g.start_level(level);g.state='play'
                if name=='crocodile':
                    enemy=g.crocodiles[0];g.hero=Hero(enemy.x-60,enemy.y)
                    g.cam=g.prev_cam=enemy.x-640
                elif level==4:
                    x,y=tower.CHECKPOINTS[0];g.checkpoint=(x-60,y)
                    g.hero=Hero(x,tower.HEIGHT+200);g.cam_y=g.prev_cam_y=tower.camera_target(y)
                else:
                    g.hero=Hero(3000,900);g.cam=g.prev_cam=2450
                g.update(STEP,0,False,False)
                for frame in range(frames):
                    pg.event.pump()
                    for _ in range(2):
                        if g.state=='play':g.update(STEP,0,False,False)
                        g.time+=STEP
                    before=g.native_canvas.uploads;active=g.resurrection.active
                    g.draw(1)
                    if active:uploads+=g.native_canvas.uploads-before
                    image=g.capture()
                    if name=='fall' and frame in (35,51,66):
                        label={35:'flight',51:'giant',66:'reborn'}[frame]
                        pg.image.save(image,ROOT/'output'/f'hero-resurrection-{label}.png')
                    writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
                sections.append(dict(cause=name,level=level,lives=g.lives,deaths=g.deaths,state=g.state,
                                     respawn_finished=not g.resurrection.active))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            data=dict(gpu=g.native_canvas.gpu,sequence_seconds=DURATION,reappear_seconds=REAPPEAR,
                      new_resurrection_texture_uploads=uploads,sections=sections)
            (ROOT/'output'/'hero-resurrection-validation.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
            print(data)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
