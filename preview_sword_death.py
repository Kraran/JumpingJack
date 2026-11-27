"""Actual skeleton sword contacts: both sides, midair, resurrection and last life."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP
from sword_death import pose_index


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory(prefix='jumpingjack-sword-') as directory:
        temp=Path(directory)
        g=Game(not native,fullscreen=False,settings_path=temp/'settings.json',saves_path=temp/'saves')
        writer=None
        try:
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                '-pix_fmt','rgb24','-s','1920x1080','-r','60','-i','-','-an','-c:v','libx264',
                '-preset','veryfast','-crf','19','-pix_fmt','yuv420p',str(ROOT/'output'/'hero-sword-death-demo.mp4')],
                stdin=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            observations=[];uploads=0;poses=set()
            cases=(('impact',5,0,-1,3,False),('reverse',7,0,1,3,False),
                   ('air',5,0,-1,3,True),('game-over',8,-1,-1,1,False))
            for name,level,index,side,lives,air in cases:
                g.new_game();g.start_level(level);g.state='play';g.sound_on=False;g.lives=lives;g.invuln=0
                g.gamepads.rumble_enabled=False
                enemy=g.hoplites[index];enemy.facing=enemy.previous_facing=side
                g.hero=Hero(enemy.x+side*(35 if air else 65),enemy.y-(46 if air else 0))
                g.hero.face=-side;g.hero.grounded=not air
                if air:g.hero.vy=180
                g.cam=g.prev_cam=max(0,min(g.world_length-1280,g.hero.x-640))
                if level==8:g.cam_y=g.prev_cam_y=enemy.y-620
                g.draw(1,present=False)
                for _ in range(90):
                    g.time+=STEP;g.update(STEP,0,False,False)
                    if g.hero_death.active:break
                assert g.hero_death.kind=='sword' and g.hero_death.active
                impact=(g.hero.x,g.hero.y);landing=None
                for frame in range(270):
                    for event in pg.event.get():
                        if event.type==pg.QUIT:raise KeyboardInterrupt('Preview cancelled')
                    for _ in range(2):
                        g.time+=STEP;g.update(STEP,0,False,False)
                    active=g.hero_death.active
                    before=g.native_canvas.uploads;g.draw(.5,present=native)
                    if active:
                        uploads+=g.native_canvas.uploads-before
                        poses.add((g.hero_death.hero_face,pose_index(g.hero_death,.5)))
                        if landing is None and g.hero_death.landed_at is not None:landing=g.hero_death.landed_at
                    if name=='impact' and frame in (5,30,75):
                        label={5:'impact',30:'collapse',75:'fallen'}[frame]
                        pg.image.save(g.capture(),ROOT/'output'/f'hero-sword-{label}.png')
                    if name=='reverse' and frame==32:pg.image.save(g.capture(),ROOT/'output'/'hero-sword-reverse.png')
                    if name=='air' and frame==3:pg.image.save(g.capture(),ROOT/'output'/'hero-sword-air.png')
                    if name=='game-over' and frame==130:pg.image.save(g.capture(),ROOT/'output'/'hero-sword-game-over.png')
                    writer.stdin.write(pg.image.tobytes(g.capture(),'RGB'))
                observations.append({'case':name,'level':level,'lives':g.lives,'deaths':g.deaths,'state':g.state,
                                     'impact':impact,'landed_at':landing,'corpse_kind':g.hero_death.kind})
                assert (g.lives,g.deaths)==(lives-1,1)
                assert g.state==('game_over' if lives==1 else 'play')
            writer.stdin.close();errors=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(errors)
            report={'gpu':g.native_canvas.gpu,'renderer':g.presentation.renderer,'authored_poses':16,
                    'prepared_poses_per_facing':64,'sprite_atlases':len(g.sword_death_sprites.images),
                    'new_death_texture_uploads':uploads,'observed_pose_samples':len(poses),'cases':observations,
                    'scope':'Real sword/body contacts with no invulnerability; temporary settings and saves; '
                            'both facings, real falling, resurrection and last-life Game Over.'}
            (ROOT/'output'/'hero-sword-death-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False,indent=2))
            assert uploads==0,report
            if native:assert g.native_canvas.gpu
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
