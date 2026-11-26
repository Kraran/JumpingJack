"""Native GPU preview of quick panic falls through a real temple pit."""
import json
from pathlib import Path
import subprocess
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP


def preview():
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as folder:
        g=Game(False,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        writer=None
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'hero-pit-death-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            sections=[];uploads=0
            for name,face,lives in (('right',1,3),('left',-1,3),('game-over',1,1)):
                g.new_game();g.start_level(3);g.state='play';g.lives=lives
                g.hero=Hero(1800.,595.);g.hero.vy=100.;g.hero.face=face;g.invuln=100
                g.cam=g.prev_cam=1288.
                for frame in range(180):
                    pg.event.pump();before=g.native_canvas.uploads
                    for _ in range(2):
                        if g.state=='play':g.update(STEP,0,False,False)
                        g.time+=STEP
                    active=g.hero_death.active;g.draw(1)
                    if active:uploads+=g.native_canvas.uploads-before
                    image=g.capture()
                    if name=='right' and frame in (11,20,29):
                        label={11:'transition',20:'panic',29:'fall'}[frame]
                        pg.image.save(image,ROOT/'output'/f'hero-pit-{label}.png')
                    if name=='game-over' and frame==100:pg.image.save(image,ROOT/'output'/'hero-pit-game-over.png')
                    writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
                assert g.hero_death.kind=='pit'
                sections.append(dict(cause=name,lives=g.lives,deaths=g.deaths,state=g.state,duration=g.hero_death.elapsed))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            report=dict(gpu=g.native_canvas.gpu,new_death_texture_uploads=uploads,sections=sections)
            (ROOT/'output'/'hero-pit-death-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':preview()
