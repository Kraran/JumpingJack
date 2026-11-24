"""Show robotic flight, reversal, and destruction with the real game renderer."""
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
             '-crf','18','-pix_fmt','yuv420p',str(output/'robot-beetle-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for stage,duration in ((0,270),(1,120)):
            game.reset();game.state='play';game.invuln=10;game.time=0
            if stage==0:game.hero=Hero(1400,620);game.hero.grounded=True
            else:game.hero=Hero(1600,570);game.hero.vy=-240
            for frame in range(duration):
                for step in range(2):
                    game.time+=STEP
                    game.update(STEP,0,False,False,fire=stage==1 and frame==6 and step==0)
                if stage==0:
                    _,x,_=game.beetles()[0];game.cam=game.prev_cam=x-640
                    key=game.beetle_motions[0].sample()
                    label='Scarabee en titane : ailes, reacteur cyan et retournement'
                else:
                    game.cam=game.prev_cam=1088
                    key=game.beetle_deaths[0].sample() if game.beetle_deaths else (
                        ('death',1,0,7) if 0 in game.dead_beetles else game.beetle_motions[0].sample())
                    label='Le rayon solaire neutralise le robot et disperse son armure'
                game.draw(1)
                if stage==0 and frame==100:pg.image.save(game.capture(),output/'robot-beetle-game.png')
                screen=pg.transform.smoothscale(game.capture(),(960,540))
                detail_key=(key,game.beetle_deaths[0].explosion_sample()) if stage==1 and game.beetle_deaths else key
                if detail_key not in details:
                    image=game.beetle_sprites.death_frame(game.beetle_deaths[0]) if stage==1 and game.beetle_deaths else game.beetle_sprites.frame(key)
                    details[detail_key]=pg.transform.smoothscale(image,(336,256))
                pg.draw.rect(screen,(25,39,47),(570,110,370,300))
                screen.blit(font.render('Detail de l animation',True,(240,220,170)),(585,118))
                screen.blit(details[detail_key],(587,150))
                pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                screen.blit(font.render(label,True,(255,227,153)),(18,511))
                if stage==0 and frame==100:pg.image.save(screen,output/'robot-beetle-preview.png')
                process.stdin.write(pg.image.tobytes(screen,'RGB'))
            if stage==1:assert 0 in game.dead_beetles
        process.stdin.close();error=process.stderr.read().decode(errors='replace');process.wait()
        if process.returncode:raise RuntimeError(error)
    finally:
        if process.poll() is None:process.kill();process.wait()
        game.close()


if __name__=='__main__':export()
