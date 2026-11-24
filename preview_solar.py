"""Export the real solar attack: ground, airborne, and denied while gliding."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import subprocess
import pygame as pg
from main import Game, Hero, ROOT, STEP


def export():
    import imageio_ffmpeg
    game=Game(True);output=ROOT/'output';output.mkdir(exist_ok=True)
    font=pg.font.SysFont('Segoe UI',21)
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
             '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
             '-crf','18','-pix_fmt','yuv420p',str(output/'solar-ray-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for stage in range(3):
            game.reset();game.state='play';game.invuln=10;game.time=0
            if stage==0:
                game.hero=Hero(700,620);game.hero.grounded=True
                label='F / B : mains jointes et rayon solaire mortel'
            elif stage==1:
                game.hero=Hero(1600,570);game.hero.vy=-240
                label='Le rayon peut aussi etre tire pendant un saut'
            else:
                game.hero=Hero(1600,500);game.hero.vy=105
                label='En vol plane : le tir reste indisponible'
            game.cam=game.prev_cam=max(0,game.hero.x-512)
            for frame in range(120):
                for step in range(2):
                    game.time+=STEP
                    game.update(STEP,0,stage==2,False,
                                fire=step==0 and frame==(15 if stage==0 else 6))
                game.draw(1)
                if stage==0 and frame==28:pg.image.save(game.capture(),output/'solar-ray-game.png')
                screen=pg.transform.smoothscale(game.capture(),(960,540))
                pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                screen.blit(font.render(label,True,(255,227,153)),(20,511))
                process.stdin.write(pg.image.tobytes(screen,'RGB'))
            if stage==0:assert not game.crocodiles[0].alive
            elif stage==1:assert 0 in game.dead_beetles
            else:assert not game.solar.active
        process.stdin.close();error=process.stderr.read().decode(errors='replace');process.wait()
        if process.returncode:raise RuntimeError(error)
    finally:
        if process.poll() is None:process.kill();process.wait()
        game.close()


if __name__=='__main__':export()
