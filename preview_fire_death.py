"""Native GPU preview of brazier deaths in the temple and tower."""
import json
from pathlib import Path
import subprocess
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP
import tower_level


def preview():
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as folder:
        g=Game(False,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        writer=None
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'hero-fire-envelope-v2-death-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            sections=[];uploads=0
            for name,level,lives in (('air',3,3),('platform',4,3),('game-over',4,1)):
                g.new_game();g.start_level(level);g.state='play';g.lives=lives
                x,y=(650.,390.) if level==3 else tower_level.TORCHES[0]
                g.hero=Hero(x,y+(35 if level==4 else 0));g.hero.grounded=level==4
                g.hero.face=-1 if name=='platform' else 1
                g.cam=g.prev_cam=max(0,x-512) if level==3 else 0.
                if level==4:g.cam_y=g.prev_cam_y=tower_level.camera_target(g.hero.y)
                g.update(STEP,0,False,False)
                assert g.hero_death.active and g.hero_death.kind=='fire'
                for frame in range(250):
                    pg.event.pump();before=g.native_canvas.uploads
                    for _ in range(2):
                        if g.state=='play':g.update(STEP,0,False,False)
                        g.time+=STEP
                    active=g.hero_death.active;g.draw(1)
                    if active:uploads+=g.native_canvas.uploads-before
                    image=g.capture()
                    if name=='air' and frame in (15,65):
                        label='burning' if frame==15 else 'collapse'
                        pg.image.save(image,ROOT/'output'/f'hero-fire-envelope-v2-{label}.png')
                    if name=='platform' and frame==85:pg.image.save(image,ROOT/'output'/'hero-fire-envelope-v2-extinction.png')
                    if name=='game-over' and frame==160:pg.image.save(image,ROOT/'output'/'hero-fire-envelope-v2-game-over.png')
                    writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
                sections.append(dict(cause=name,level=level,lives=g.lives,deaths=g.deaths,state=g.state,
                                     landed_at=g.hero_death.landed_at,duration=g.hero_death.elapsed))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            report=dict(gpu=g.native_canvas.gpu,new_death_texture_uploads=uploads,sections=sections)
            (ROOT/'output'/'hero-fire-envelope-v2-death-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':preview()
