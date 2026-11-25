"""Real solar kill of a temple scorpion, normal speed then slow motion."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP
from scorpion import Scorpion,DEATH_TIME,DEATH_FRAMES,EXPLOSION_SIZE


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                     '-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'scorpion-explosion-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0;captured=set();font=pg.font.SysFont('Segoe UI',18)
            for slow,frames in ((1,180),(2,300)):
                game.start_level(3);game.state='play';game.sound_on=False
                game.beetle_motions=[];game.scorpions=[Scorpion(0)]
                game.hero=Hero(1100,620);game.hero.grounded=True;game.hero.face=1;game.invuln=0
                game.hero_animation.reset()
                for frame in range(frames):
                    pg.event.pump()
                    for step in range(2):
                        game.time+=STEP/slow
                        game.update(STEP/slow,0,False,False,fire=frame==18*slow and step==0,down=True)
                    game.cam=game.prev_cam=850;before=game.native_canvas.uploads;game.draw(1)
                    uploads+=game.native_canvas.uploads-before
                    image=game.capture();enemy=game.scorpions[0]
                    if slow==1 and not enemy.alive:
                        for label,age in (('flames',.22),('smoke',.7)):
                            if label not in captured and enemy.death_timer>=age:
                                pg.image.save(image,ROOT/'output'/f'scorpion-explosion-{label}.png');captured.add(label)
                    image=pg.transform.smoothscale(image,(1280,720))
                    pg.draw.rect(image,(12,26,33),(0,680,1280,40))
                    label='Vitesse normale' if slow==1 else 'Ralenti ×2'
                    image.blit(font.render(f'Exécuteur · explosion, flammes et débris · {label}',True,(245,217,160)),(18,688))
                    writer.stdin.write(pg.image.tobytes(image,'RGB'))
                assert not game.scorpions[0].alive and game.scorpions[0].death_timer>DEATH_TIME
                assert game.lives==3
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            (ROOT/'output'/'scorpion-explosion-validation.json').write_text(json.dumps({
                'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,'new_texture_uploads':uploads,
                'death_duration':DEATH_TIME,'death_frames':DEATH_FRAMES,'flame_size_native':EXPLOSION_SIZE,
                'scarab_flame_size_native':[120,80],'atlas_pages':[im.get_size() for im in game.scorpion_sprites.images],
                'real_solar_kill':True,'lives':game.lives},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
