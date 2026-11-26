"""Real upward blade contacts, both facings, tower and final-life playback."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP
from hero_death import BLADE_DURATION,FRAMES
from blade_death import POSE_TIME
from spikes import teeth,SPIKE_DEPTH
import tower_level


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as folder:
        g=Game(not native,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        writer=None
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'hero-blade-death-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            sections=[];uploads=0;seen=set()
            for name,level,face,lives in (('impact',1,1,3),('tower',4,-1,3),('game-over',1,-1,1)):
                g.new_game();g.start_level(level);g.state='play';g.lives=lives;g.invuln=100
                platform=next(p for p in g.platforms if p.spiked)
                left,right=next(teeth(platform))
                g.hero=Hero((left+right)/2,platform.y+platform.h+SPIKE_DEPTH+54+8)
                g.hero.vy=-600;g.hero.face=face
                g.cam=g.prev_cam=max(0,min(g.world_length-1280,g.hero.x-640)) if level!=4 else 0.
                if level==4:g.cam_y=g.prev_cam_y=tower_level.camera_target(g.hero.y)
                for _ in range(10):
                    g.update(STEP,0,False,False)
                    if g.hero_death.active:break
                assert g.hero_death.active and g.hero_death.kind=='blade'
                for frame in range(210):
                    pg.event.pump();before=g.native_canvas.uploads
                    for _ in range(2):
                        if g.state=='play':g.update(STEP,0,False,False)
                        g.time+=STEP
                    active=g.hero_death.active;g.draw(1)
                    if active:
                        uploads+=g.native_canvas.uploads-before
                        seen.add((face,min(FRAMES-1,int(g.hero_death.elapsed/POSE_TIME*(FRAMES-1)))))
                    image=g.capture()
                    if name=='impact' and frame in (7,44):
                        label='impact' if frame==7 else 'collapse'
                        pg.image.save(image,ROOT/'output'/f'hero-blade-{label}.png')
                    if name=='tower' and frame==25:pg.image.save(image,ROOT/'output'/'hero-blade-tower.png')
                    if name=='game-over' and frame==100:pg.image.save(image,ROOT/'output'/'hero-blade-game-over.png')
                    writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
                sections.append(dict(cause=name,level=level,lives=g.lives,deaths=g.deaths,state=g.state))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            report=dict(gpu=g.native_canvas.gpu,sequence_seconds=BLADE_DURATION,poses_per_facing=FRAMES,
                        observed_poses=len(seen),new_death_texture_uploads=uploads,sections=sections)
            (ROOT/'output'/'hero-blade-death-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
