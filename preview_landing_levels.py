"""Export the three fall receptions and a glide using the game's physics."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import subprocess
import pygame as pg
from main import Hero, Platform, STEP, ROOT
from hero_animation import HeroAnimator, load_bank


def export():
    import imageio_ffmpeg
    pg.init();pg.display.set_mode((64,64))
    bank=load_bank(ROOT/'assets');output=ROOT/'output';output.mkdir(exist_ok=True)
    screen=pg.Surface((1280,500));font=pg.font.SysFont('Segoe UI',22)
    small=pg.font.SysFont('Segoe UI',18)
    images={id(p):pg.transform.scale(p.images[0],(216,216))
            for clip in bank.clips.values() for p in clip}
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
             '-pix_fmt','rgb24','-s','1280x500','-r','60','-i','-','-an','-c:v','libx264',
             '-crf','18','-pix_fmt','yuv420p',str(output/'hero-landing-levels-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for frame in range(480):
            if frame%240==0:
                cases=[(Hero(500,620-height),HeroAnimator(),glide,label)
                       for height,glide,label in ((95,False,'Petite chute / 95'),
                           (200,False,'Chute moyenne / 200'),(320,False,'Grande chute / 320'),
                           (320,True,'Arrivee en planant / 320'))]
            screen.fill((25,39,47))
            for i,(hero,animation,glide,label) in enumerate(cases):
                floor=[Platform(0,620,2000,100,True)]
                for _ in range(2):
                    was=hero.grounded;hero.update(STEP,0,glide,False,floor)
                    animation.update(STEP,hero,was)
                left=i*320;root_x=left+180;root_y=450+round((hero.y-620)*.5)
                pg.draw.rect(screen,(157,126,79),(left+10,450,300,20))
                screen.blit(font.render(label,True,(237,214,166)),(left+12,15))
                pose=animation.sample(bank);px,py=pose.pivot
                screen.blit(images[id(pose)],(root_x-round(px*1.8),root_y-round(py*1.8)))
                status=f'Recuperation : {hero.recovery:.2f} s' if hero.recovery else (
                    'Pret a repartir' if hero.grounded else 'Descente')
                screen.blit(small.render(status,True,(204,220,220)),(left+12,478))
            if cases[2][1].state=='land_heavy' and .22<cases[2][1].elapsed<.24:
                pg.image.save(screen,output/'hero-landing-levels-preview.png')
            process.stdin.write(pg.image.tobytes(screen,'RGB'))
        process.stdin.close();error=process.stderr.read().decode(errors='replace');process.wait()
        if process.returncode:raise RuntimeError(error)
    finally:
        if process.poll() is None:process.kill();process.wait()
        pg.quit()


if __name__=='__main__':export()
