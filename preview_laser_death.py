"""Native staged laser contacts: horizontal, angled airborne, final tower life."""
import json
import math
from pathlib import Path
import subprocess
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP
from scorpion import LaserBolt
from laser_death import pose_position
from hero_death import FRAMES
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
                str(ROOT/'output'/'hero-laser-death-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            sections=[];uploads=0;seen=set()
            for name,level,angle,sign,lives in (('ground',3,0,-1,3),('air',3,60,1,3),('game-over',4,0,-1,1)):
                g.new_game();g.start_level(level);g.state='play';g.lives=lives
                x,y=(350.,300. if name=='air' else 620.) if level==3 else tower_level.START
                g.hero=Hero(x,y);g.hero.grounded=name!='air';g.hero.face=-sign
                dx=math.cos(math.radians(angle))*sign;dy=-math.sin(math.radians(angle))
                g.laser_bolts=[LaserBolt(x-dx*80,y-27-dy*80,dx*660,dy*660)]
                g.cam=g.prev_cam=max(0,min(g.world_length-1280,x-512)) if level==3 else 0.
                if level==4:g.cam_y=g.prev_cam_y=tower_level.camera_target(y)
                attacker=g.scorpions[0];attacker.x=attacker.px=x-sign*250
                attacker.facing=attacker.previous_facing=sign
                attacker.state=attacker.previous_state='recoil';attacker.timer=attacker.previous_timer=0.
                attacker.angle=attacker.previous_angle=angle
                for _ in range(40):
                    g.update(STEP,0,False,False)
                    if g.hero_death.active:break
                assert g.hero_death.active and g.hero_death.kind=='laser'
                for frame in range(230):
                    pg.event.pump();before=g.native_canvas.uploads
                    for _ in range(2):
                        if g.state=='play':g.update(STEP,0,False,False)
                        g.time+=STEP
                    active=g.hero_death.active;g.draw(1)
                    if active:
                        uploads+=g.native_canvas.uploads-before
                        seen.add((g.hero_death.hero_face,int(pose_position(g.hero_death,g.hero_death.elapsed)/15*(FRAMES-1))))
                    image=g.capture()
                    if name=='ground' and frame in (7,36):
                        label='impact' if frame==7 else 'collapse'
                        pg.image.save(image,ROOT/'output'/f'hero-laser-{label}.png')
                    if name=='air' and frame==25:pg.image.save(image,ROOT/'output'/'hero-laser-air.png')
                    if name=='game-over' and frame==120:pg.image.save(image,ROOT/'output'/'hero-laser-game-over.png')
                    writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
                sections.append(dict(cause=name,level=level,lives=g.lives,deaths=g.deaths,state=g.state,
                                     landed_at=g.hero_death.landed_at,duration=g.hero_death.elapsed))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            report=dict(gpu=g.native_canvas.gpu,poses_per_facing=FRAMES,observed_poses=len(seen),
                        new_death_texture_uploads=uploads,sections=sections)
            (ROOT/'output'/'hero-laser-death-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':preview()
