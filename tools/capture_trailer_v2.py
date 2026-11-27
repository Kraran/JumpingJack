"""Native trailer footage: real collisions, no invulnerability and current solar FX."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame as pg
from main import Game,Hero,STEP,ROOT
from terrain import sand_height
from settings import Settings
from scorpion import LaserBolt
from greece_levels import LEVELS
from preview_hoplite import arena
import imageio_ffmpeg
import tower_level
from preview_tower import controls as tower_controls

WORK=ROOT/'output/trailer-work-v2'


def capture(from_shot=None):
    WORK.mkdir(exist_ok=True)
    observations=[]
    with tempfile.TemporaryDirectory(prefix='jumpingjack-trailer-v2-') as directory:
        temp=Path(directory);settings=temp/'settings.json'
        Settings(fullscreen=False,music=False).save(settings)
        g=Game(False,fullscreen=False,settings_path=settings,saves_path=temp/'saves')
        try:
            # Each shot is independent; campaign enemy collisions remain active.
            shots=[('egypt-1',1,160,2.5),('egypt-2',2,260,2.5),('egypt-3',3,160,2.),
                   ('tower',4,0,1.5),('greece-5',5,160,2.),('greece-6',6,7000,1.5),
                   ('greece-7',7,160,1.5),('acropolis',8,13000,3.),
                   ('solar',5,0,3.5),('crocodile',1,0,2.),('fire',3,0,2.),
                   ('sword',5,0,2.),('laser',3,0,2.),('water',2,0,2.)]
            if from_shot is not None:shots=shots[next(i for i,shot in enumerate(shots) if shot[0]==from_shot):]
            for name,level,x,seconds in shots:
                g.new_game();g.start_level(level);g.state='play';g.sound_on=False
                g.gamepads.rumble_enabled=False;g.invuln=0
                death=name in ('crocodile','fire','sword','laser','water')
                scenic=name.startswith(('egypt','greece')) or name in ('acropolis','tower')
                target=None
                if scenic:
                    y=LEVELS[level].floor_height(x) if level>=5 else sand_height(x) if level==2 else 620
                    g.hero=Hero(x,y);g.hero.grounded=True
                    if name=='tower':g.hero=Hero(*tower_level.START);g.hero.grounded=True
                    # Closing landscape stays away from the next hoplite.
                    if name=='acropolis':g.hero=Hero(12800,380);g.hero.grounded=True
                elif name=='solar':
                    target=arena(g,'defeated');g.invuln=0
                elif name=='crocodile':
                    enemy=g.crocodiles[0];enemy.facing=enemy.previous_facing=-1
                    g.hero=Hero(enemy.x-60,enemy.y);g.hero.grounded=True
                elif name=='fire':
                    g.hero=Hero(650,390)
                elif name=='sword':
                    enemy=g.hoplites[0];enemy.facing=enemy.previous_facing=-1
                    g.hero=Hero(enemy.x-65,enemy.y);g.hero.grounded=True
                elif name=='laser':
                    g.hero=Hero(350,620);g.hero.grounded=True
                    g.laser_bolts=[LaserBolt(430,593,-660,0)]
                elif name=='water':
                    g.hero=Hero(1150,580);g.hero.vy=350;g.hero.vx=160
                g.hero.face=1
                g.cam=g.prev_cam=max(0,min(g.world_length-1280,g.hero.x-480))
                if level==8:g.cam_y=g.prev_cam_y=LEVELS[8].floor_height(g.hero.x)-620
                if name=='tower':
                    g.cam_y=g.prev_cam_y=tower_level.camera_target(g.hero.y)
                    tower_action=iter(tower_controls(g,tower_level.route_platforms(g.platforms)[:2]))
                if death:
                    # Keep the lead-in to contact, so the sword stroke and laser are visible.
                    if name in ('crocodile','fire'):
                        g.update(STEP,0,False,False)
                        assert g.hero_death.active,(name,'contact did not trigger')
                writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-y','-loglevel','error',
                    '-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','60','-i','-',
                    '-an','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',
                    str(WORK/f'{name}.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                kinds=set();beam_frames=0;invulnerability=[]
                try:
                    for frame in range(round(seconds*60)):
                        for event in pg.event.get():
                            if event.type==pg.QUIT:raise KeyboardInterrupt()
                        # The solar close-up alone uses 0.5x speed, retaining the actual shader/pose timings.
                        for step in range(1 if name=='solar' else 2):
                            g.time+=STEP
                            axis=0 if death or name in ('solar','acropolis') else 1
                            if name.startswith('egypt') and frame>=65:axis=0
                            jump=scenic and name!='acropolis' and frame==10 and step==0
                            if name=='tower':axis,jump=next(tower_action,(0,False))
                            g.update(STEP,axis,scenic and name!='acropolis',jump,
                                     fire=name=='solar' and frame==12 and step==0)
                        invulnerability.append(g.invuln)
                        if g.hero_death.active:kinds.add(g.hero_death.kind)
                        if g.solar.visual_elapsed is not None:beam_frames+=1
                        g.draw(.5,present=True)
                        writer.stdin.write(pg.image.tobytes(g.capture(),'RGB'))
                    writer.stdin.close();errors=writer.stderr.read().decode(errors='replace');writer.wait()
                    if writer.returncode:raise RuntimeError(errors)
                finally:
                    if writer.poll() is None:writer.kill();writer.wait()
                if scenic:assert g.deaths==0,(name,'unsafe traversal',kinds)
                if death:assert name in kinds,(name,kinds)
                if target is not None:assert not target.alive and beam_frames>=40,(target.alive,beam_frames)
                # Any protection here could only be the game's own post-resurrection interval.
                observations.append({'shot':name,'level':level,'deaths':g.deaths,'death_kinds':sorted(kinds),
                                     'solar_effect_frames':beam_frames,'enemy_defeated':None if target is None else not target.alive,
                                     'capture_invulnerability':False,'speed':.5 if name=='solar' else 1.})
                print(json.dumps(observations[-1]),flush=True)
            assert g.native_canvas.gpu
            (WORK/'capture-validation.json').write_text(json.dumps(observations,indent=2),encoding='utf-8')
        finally:g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--from-shot')
    capture(parser.parse_args().from_shot)
