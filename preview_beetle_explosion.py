"""Show the complete fiery scarab destruction at normal speed and slow motion."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import subprocess
import pygame as pg
from main import Game,Hero,STEP,ROOT


def export():
    import imageio_ffmpeg
    game=Game(True);output=ROOT/'output';output.mkdir(exist_ok=True)
    font=pg.font.SysFont('Segoe UI',20);details={}
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
             '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
             '-crf','18','-pix_fmt','yuv420p',str(output/'beetle-explosion-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for slow,frames in ((1,120),(3,240)):
            game.reset();game.state='play';game.time=0;game.hero=Hero(1600,570);game.hero.vy=-240
            for frame in range(frames):
                for step in range(2):
                    dt=STEP/slow;game.time+=dt
                    game.update(dt,0,False,False,fire=frame==6*slow and step==0)
                game.cam=game.prev_cam=1088;game.draw(1)
                screen=pg.transform.smoothscale(game.capture(),(960,540))
                death=game.beetle_deaths[0] if game.beetle_deaths else None
                key=(death.sample(),death.explosion_sample()) if death else (
                    ('gone',) if 0 in game.dead_beetles else game.beetle_motions[0].sample())
                if key not in details:
                    image=game.beetle_sprites.death_frame(death) if death else (
                        pg.Surface((168,128),pg.SRCALPHA) if key==('gone',) else game.beetle_sprites.frame(key))
                    details[key]=pg.transform.smoothscale(image,(336,256))
                pg.draw.rect(screen,(25,39,47),(570,110,370,300))
                screen.blit(font.render('Flammes, metal et fumee',True,(240,220,170)),(585,118))
                screen.blit(details[key],(587,150))
                pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                label='Vitesse normale' if slow==1 else 'Ralenti x3'
                screen.blit(font.render(label,True,(255,227,153)),(18,511))
                if slow==1 and frame==24:
                    pg.image.save(screen,output/'beetle-explosion-preview.png')
                    pg.image.save(game.capture(),output/'beetle-explosion-game.png')
                process.stdin.write(pg.image.tobytes(screen,'RGB'))
            assert 0 in game.dead_beetles and not game.beetle_deaths
        process.stdin.close();error=process.stderr.read().decode(errors='replace');process.wait()
        if process.returncode:raise RuntimeError(error)
    finally:
        if process.poll() is None:process.kill();process.wait()
        game.close()


if __name__=='__main__':export()
