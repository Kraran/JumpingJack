"""Export actual platform-drop physics at normal speed and slow motion."""
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
    screen=pg.Surface((960,600));font=pg.font.SysFont('Segoe UI',23)
    images={id(p):tuple(pg.transform.scale(im,(180,180)) for im in p.images)
            for clip in bank.clips.values() for p in clip}
    platforms=[Platform(400,300,200,32),Platform(400,500,200,32),Platform(0,700,1000,100,True)]
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
             '-pix_fmt','rgb24','-s','960x600','-r','60','-i','-','-an','-c:v','libx264',
             '-crf','18','-pix_fmt','yuv420p',str(output/'hero-drop-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for frame in range(360):
            if frame%180==0:
                cases=[]
                for face in (1,-1):
                    hero=Hero(500,300);hero.grounded=True;hero.face=face
                    animation=HeroAnimator();animation.turn=animation.previous_turn=0. if face>0 else 1.
                    cases.append([hero,animation,0])
            screen.fill((25,39,47))
            for i,case in enumerate(cases):
                hero,animation,tick=case
                if i==0 or frame%3==0:
                    for _ in range(2):
                        was=hero.grounded
                        hero.update(STEP,0,True,tick==0,platforms,drop=tick==0)
                        animation.update(STEP,hero,was);tick+=1
                case[2]=tick;left=i*480
                label='Vitesse normale' if i==0 else 'Ralenti x3 / sens oppose'
                screen.blit(font.render(label,True,(237,214,166)),(left+25,15))
                for platform in platforms:
                    y=220+round((platform.y-300)*.9)
                    pg.draw.rect(screen,(157,126,79),(left+65,y,350,10))
                pose=animation.sample(bank);facing=animation.render_facing()
                px,py=pose.pivot
                if facing<0:px=119-px
                screen.blit(images[id(pose)][0 if facing>0 else 1],
                            (left+250-round(px*1.5),220+round((hero.y-300)*.9)-round(py*1.5)))
                screen.blit(font.render('Bas + saut',True,(204,220,220)),(left+25,545))
            if cases[0][1].state=='drop' and .13<cases[0][1].elapsed<.15:
                pg.image.save(screen,output/'hero-drop-preview.png')
            process.stdin.write(pg.image.tobytes(screen,'RGB'))
        process.stdin.close();error=process.stderr.read().decode(errors='replace');process.wait()
        if process.returncode:raise RuntimeError(error)
    finally:
        if process.poll() is None:process.kill();process.wait()
        pg.quit()


if __name__=='__main__':export()
