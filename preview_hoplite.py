"""Controlled real-AI footage of the Bronze Guardian, including GPU checks."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP,GOLD
from hoplite import Hoplite


SHOTS=(('patrol',240,'PATROUILLE LENTE ET DEMI-TOUR'),
       ('pursuit',240,'DÉTECTION DU HÉROS ET POURSUITE RAPIDE'),
       ('attack',120,'ATTAQUE À L’ÉPÉE COURTE'),
       ('defeated',180,'RAYON SOLAIRE ET EFFONDREMENT'))


def arena(game,name):
    game.new_game();game.start_level(5);game.state='play';game.sound_on=False;game.invuln=0
    game.beetle_motions=[];game.vultures=[];game.scorpions=[];game.gyrospheres=[]
    guard=Hoplite(10000,9800,11000,9590,12000,620,1)
    game.hoplites=[guard]
    x=11800 if name=='patrol' else 10520 if name=='pursuit' else 10065 if name=='attack' else 9850
    if name=='patrol':guard.x=guard.px=9820;guard.facing=guard.previous_facing=-1
    if name=='defeated':guard.facing=guard.previous_facing=-1
    game.hero=Hero(x,620);game.hero.grounded=True
    game.cam=game.prev_cam=guard.x-480
    return guard


def preview(native=False,video=False):
    writer=None;output=ROOT/'output';output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='jumpingjack-hoplite-') as directory:
        temp=Path(directory)
        g=Game(not native,fullscreen=False,settings_path=temp/'settings.json',saves_path=temp/'saves')
        try:
            for _,_,label in SHOTS:g.cache_text(label,16,GOLD,outlined=True)
            g.native_canvas.preload(list(g.text_cache.values()))
            if video:
                import imageio_ffmpeg
                writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error',
                    '-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','60','-i','-',
                    '-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
                    str(output/'hoplite-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            observations=[]
            for name,frames,label in SHOTS:
                guard=arena(g,name);states=set();travel=0.
                g.draw(1,present=False)
                g.text(label,(640,686),16,GOLD,center=True,outlined=True)
                uploads=g.native_canvas.uploads
                for frame in range(frames):
                    for event in pg.event.get():
                        if event.type==pg.QUIT:raise KeyboardInterrupt('Preview cancelled')
                    for step in range(2):
                        previous=guard.x
                        g.time+=STEP
                        g.update(STEP,1 if name=='pursuit' else 0,False,False,
                                 fire=name=='defeated' and frame==0 and step==0)
                        travel+=abs(guard.x-previous);states.add(guard.state)
                    # Controlled camera follows the guardian while real hero and
                    # enemy physics, vision, damage and solar energy stay active.
                    camera=max(0,min(g.world_length-1280,guard.x-480))
                    g.cam=g.prev_cam=camera
                    g.draw(.5,present=False)
                    g.text(label,(640,686),16,GOLD,center=True,outlined=True)
                    if native:g.native_canvas.present(g.screen)
                    capture_frame=frames-15 if name=='defeated' else 90 if name=='pursuit' else 18 if name=='attack' else 140
                    if frame==capture_frame:pg.image.save(g.capture(),output/f'hoplite-{name}.png')
                    if writer:writer.stdin.write(pg.image.tobytes(g.capture(),'RGB'))
                observations.append({'shot':name,'states':sorted(states),'distance':round(travel,2),
                    'alive':guard.alive,'hero_deaths':g.deaths,'score':g.score,'energy':g.energy.value,
                    'new_texture_uploads':g.native_canvas.uploads-uploads})
            if writer:
                writer.stdin.close();errors=writer.stderr.read().decode(errors='replace');writer.wait()
                if writer.returncode:raise RuntimeError(errors)
            report={'gpu':g.native_canvas.gpu,'renderer':g.presentation.renderer,
                    'pose_counts':{key:len(value) for key,value in g.hoplite_sprites.clips.items()},
                    'sprite_atlases':len(g.hoplite_sprites.images),'shots':observations,
                    'scope':'Controlled arena on real level 05 geometry; real AI and damage, '
                            'no invulnerability, unrelated enemies omitted, no campaign save writes.'}
            (output/'hoplite-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False,indent=2))
            assert 'turn' in observations[0]['states']
            assert 'alert' in observations[1]['states'] and 'chase' in observations[1]['states']
            assert observations[2]['hero_deaths']==1
            assert not observations[3]['alive'] and observations[3]['score']>=100
            assert all(not shot['new_texture_uploads'] for shot in observations),report
            if native:assert g.native_canvas.gpu
        finally:
            if writer and writer.poll() is None:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    parser.add_argument('--video',action='store_true');args=parser.parse_args()
    preview(args.native_check,args.video)
