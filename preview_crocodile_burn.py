"""Real solar incineration in both directions, with a slower second view."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import subprocess
import pygame as pg
from main import Game,Hero,STEP,ROOT
from crocodile import BURN_TIME


def export():
    import imageio_ffmpeg
    game=Game(True);output=ROOT/'output';output.mkdir(exist_ok=True)
    font=pg.font.SysFont('Segoe UI',20);details={}
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
             '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
             '-crf','18','-pix_fmt','yuv420p',str(output/'crocodile-burn-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for side,slow,frames in ((-1,1,180),(1,2,240)):
            game.reset();game.state='play';game.time=0
            game.hero=Hero(700 if side<0 else 1400,620);game.hero.grounded=True;game.hero.face=-side
            enemy=game.crocodiles[0];enemy.facing=enemy.previous_facing=side
            for frame in range(frames):
                for step in range(2):
                    dt=STEP/slow;game.time+=dt
                    game.update(dt,0,False,False,fire=frame==6*slow and step==0)
                game.cam=game.prev_cam=400;game.draw(1)
                screen=pg.transform.smoothscale(game.capture(),(960,540))
                pose=game.crocodile_sprites.sample(enemy,1);face=0 if enemy.facing>0 else 1
                key=(id(pose),face)
                if key not in details:
                    image=pose.images[face];details[key]=pg.transform.smoothscale(image,(422,round(image.get_height()*422/384)))
                px,py=pose.pivot
                if face:px=383-px
                pg.draw.rect(screen,(25,39,47),(210,70,560,285))
                screen.blit(font.render('Combustion puis cendres',True,(240,220,170)),(230,80))
                screen.blit(details[key],(500-round(px*422/384),320-round(py*422/384)))
                pg.draw.line(screen,(196,158,96),(230,320),(750,320),1)
                pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                label='Vitesse normale — aucune explosion' if slow==1 else 'Sens oppose — ralenti x2'
                screen.blit(font.render(label,True,(255,227,153)),(18,511))
                if slow==1 and frame==36:
                    pg.image.save(screen,output/'crocodile-burn-preview.png')
                    pg.image.save(game.capture(),output/'crocodile-burn-game.png')
                process.stdin.write(pg.image.tobytes(screen,'RGB'))
            assert not enemy.alive and enemy.death_timer==BURN_TIME and game.deaths==0
        process.stdin.close();error=process.stderr.read().decode(errors='replace');process.wait()
        if process.returncode:raise RuntimeError(error)
    finally:
        if process.poll() is None:process.kill();process.wait()
        game.close()


if __name__=='__main__':export()
