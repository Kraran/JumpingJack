"""Exécuteur animation gallery and real in-level crouched solar kill."""
import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP
from scorpion import Scorpion,TURN_FRAMES


def preview(native=False,turn_only=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            game.start_level(3);game.state='play';game.sound_on=False;game.invuln=100
            game.beetle_motions=[];game.hero=Hero(1100,620);game.hero.grounded=True
            game.scorpions=[Scorpion(0)];game.cam=game.prev_cam=850
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                     '-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/('scorpion-turn-v3-demo.mp4' if turn_only else 'scorpion-executor-demo.mp4'))]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0;shots=0;angles=set();walk_frames=set();font=pg.font.SysFont('Segoe UI',18)
            def draw(label,capture=None):
                nonlocal uploads
                game.cam=game.prev_cam=850;protection=game.invuln;game.invuln=0
                before=game.native_canvas.uploads
                try:game.draw(1)
                finally:game.invuln=protection
                uploads+=game.native_canvas.uploads-before
                image=game.capture()
                if capture:pg.image.save(image,ROOT/'output'/capture)
                image=pg.transform.smoothscale(image,(1280,720))
                pg.draw.rect(image,(12,26,33),(0,680,1280,40))
                image.blit(font.render(label,True,(245,217,160)),(18,688))
                writer.stdin.write(pg.image.tobytes(image,'RGB'))
            if turn_only:
                enemy=game.scorpions[0]
                for frame in range(240):
                    pg.event.pump();game.time+=1/60;game.elapsed+=1/60
                    if frame in (40,150):
                        enemy.turn_from=enemy.facing;enemy.turn_to=-enemy.facing;enemy.change('turn')
                    for _ in range(2):enemy.update(STEP,game.hero,game.platforms,can_attack=False)
                    draw('Exécuteur · pivot en volume, appuis des pattes et contrepoids de la queue',
                         'scorpion-tail-attached.png' if frame==20 else 'scorpion-turn-v3.png' if frame==54 else None)
                writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
                if writer.returncode:raise RuntimeError(error)
                assert enemy.facing==-1
                (ROOT/'output'/'scorpion-turn-validation.json').write_text(json.dumps({
                    'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                    'new_texture_uploads':uploads,'both_turns_completed':True,
                    'duration':.48,'rendered_poses':TURN_FRAMES,'source_views':5,
                    'atlas_pages':[image.get_size() for image in game.scorpion_sprites.images]},indent=2),encoding='utf-8')
                return
            for frame in range(120):
                pg.event.pump();game.time+=1/60;game.elapsed+=1/60
                for _ in range(2):game.scorpions[0].update(STEP,game.hero,game.platforms,can_attack=False)
                enemy=game.scorpions[0];walk_frames.add(int(enemy.distance/42*24)%24)
                draw('Exécuteur · marche articulée, 24 poses et queue mécanique','scorpion-walking.png' if frame==60 else None)
            enemy=game.scorpions[0];enemy.x=enemy.px=enemy.left+1
            turned=False
            for frame in range(60):
                pg.event.pump();game.time+=1/60;game.elapsed+=1/60
                for _ in range(2):enemy.update(STEP,game.hero,game.platforms,can_attack=False)
                turned=turned or enemy.facing==1
                draw('Exécuteur · retournement et reprise de la marche',
                     'scorpion-turn.png' if frame==9 else None)
            # A clear shooting gallery isolates the full aiming arc; the last
            # section restores the actual level geometry and normal simulation.
            game.platforms=[p for p in game.platforms if p.ground]
            for target_angle in (0,18,36,54,72,90):
                enemy=Scorpion(0);game.scorpions=[enemy];game.laser_bolts=[]
                x,y=enemy.pivot();a=math.radians(target_angle)
                game.hero=Hero(x-math.cos(a)*280,y-math.sin(a)*280+27)
                game.hero_animation.reset()
                for frame in range(90):
                    pg.event.pump();game.time+=1/60;game.elapsed+=1/60
                    for _ in range(2):
                        bolt=enemy.update(STEP,game.hero,game.platforms)
                        if bolt is not None:game.laser_bolts.append(bolt);shots+=1
                        for projectile in game.laser_bolts:projectile.update(STEP,game.hero,game.platforms,can_hit=False)
                        game.laser_bolts=[bolt for bolt in game.laser_bolts if bolt.alive]
                    angles.add(round(enemy.angle));draw(f'Galerie de tir · visée {target_angle}° · charge, tir et recul',
                        f'scorpion-aim-{target_angle}.png' if frame==44 else None)
            game.start_level(3);game.beetle_motions=[];game.scorpions=[Scorpion(0)];game.state='play'
            game.hero=Hero(1100,620);game.hero.grounded=True;game.hero.face=1;game.invuln=0
            game.hero_animation.reset()
            for frame in range(150):
                pg.event.pump()
                for step in range(2):
                    game.time+=STEP;game.update(STEP,0,False,False,fire=frame==30 and step==0,down=True)
                draw('Dans le temple · le héros vise accroupi et détruit le scorpion au rayon solaire',
                     'scorpion-destruction.png' if frame==50 else None)
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert shots==6 and min(angles)==0 and max(angles)==90 and len(walk_frames)==24
            assert turned
            assert not game.scorpions[0].alive and game.lives==3
            (ROOT/'output'/'scorpion-validation.json').write_text(json.dumps({'gpu':game.native_canvas.gpu,
                'renderer':game.presentation.renderer,'new_texture_uploads':uploads,'walk_poses_seen':len(walk_frames),
                'aim_min':min(angles),'aim_max':max(angles),'shots':shots,'lives':game.lives,
                'turn_completed':turned,
                'atlas_size':game.scorpion_sprites.atlas.get_size(),
                'scope':'Animation/shooting gallery with protected target, then actual temple geometry and real solar kill.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    parser.add_argument('--turn-only',action='store_true');args=parser.parse_args()
    preview(args.native_check,args.turn_only)
