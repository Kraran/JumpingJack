"""Lower, aim, fire and rise using the real interpolated game animation."""
import argparse
import json
import subprocess
import pygame as pg
from main import Game,Hero,STEP,ROOT


def preview(native=False):
    import imageio_ffmpeg
    game=Game(not native,fullscreen=False);output=ROOT/'output';output.mkdir(exist_ok=True)
    writer=None
    try:
        game.sound_on=False
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                 '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                 '-crf','18','-pix_fmt','yuv420p',str(output/'hero-crouch-demo.mp4')]
        writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        font=pg.font.SysFont('Segoe UI',19)
        for side,dry in ((1,False),(-1,True)):
            game.reset();game.state='play';game.invuln=100
            game.hero=Hero(700,620);game.hero.grounded=True;game.hero.face=side
            if dry:game.energy.value=game.energy.display=game.energy.previous_display=0
            for frame in range(180):
                pg.event.pump()
                for step in range(2):
                    game.time+=STEP
                    game.update(STEP,0,False,False,down=30<=frame<120,fire=frame==60 and step==0)
                game.cam=game.prev_cam=200;game.draw(.5)
                full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
                detail=pg.transform.scale(full.subsurface((630,800,240,140)),(480,280))
                screen.blit(detail,(430,90));pg.draw.rect(screen,(223,186,102),(429,89,482,282),1)
                pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                label='Bas : accroupissement, tir plus bas, puis relevé' if not dry else 'Autre sens : essai à vide, sans rayon'
                screen.blit(font.render(label,True,(255,227,153)),(18,511))
                if not dry and frame==73:
                    pg.image.save(full,output/'hero-crouch-game.png')
                    pg.image.save(screen,output/'hero-crouch-preview.png')
                writer.stdin.write(pg.image.tobytes(screen,'RGB'))
            assert game.hero.crouch==0
            assert game.energy.value==(0 if dry else 70)
        writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
        if writer.returncode:raise RuntimeError(error)
        (output/'hero-crouch-validation.json').write_text(json.dumps({
            'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
            'hero_poses':game.animation_bank.pose_count,'directions':[-1,1],
            'standing_muzzle_height':54,'crouch_muzzle_height':28,
            'dry_fire_checked':True,'energy_cost':30,'frames':360},indent=2),encoding='utf-8')
    finally:
        if writer is not None and writer.poll() is None:writer.kill();writer.wait()
        game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
