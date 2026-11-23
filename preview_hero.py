"""Export a 60 FPS comparison using the game's actual animation frames."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
from pathlib import Path
import subprocess
import pygame as pg
from main import Game, ROOT, STEP


def export():
    import imageio_ffmpeg  # optional developer-only video encoder
    game=Game(True)
    output=ROOT/'output';output.mkdir(exist_ok=True)
    size=(860,460);screen=pg.Surface(size)
    font=pg.font.SysFont('Segoe UI',24)
    old=[pg.transform.scale(pair[0],(pair[0].get_width()*3,pair[0].get_height()*3)) for pair in game.hero_sprites]
    scaled={id(p):pg.transform.scale(p.images[0],(p.images[0].get_width()*3,p.images[0].get_height()*3))
            for clip in game.animation_bank.clips.values() for p in clip}
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
             '-s','860x460','-r','60','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','18',
             '-pix_fmt','yuv420p',str(output/'hero-course-compare.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    hero=game.hero;hero.vx=340;hero.grounded=True
    try:
        for frame in range(480):
            if frame==240:
                game.hero_animation.reset();hero.grounded=False;hero.floating=True;hero.vy=105
            for _ in range(2):
                hero.px=hero.x;hero.x+=340*STEP
                game.hero_animation.update(STEP,hero,hero.grounded)
            pose=game.hero_animation.sample(game.animation_bank,1)
            screen.fill((22,39,46))
            pg.draw.line(screen,(237,194,105),(0,400),(860,400))
            title1,title2=('Avant : 4 poses','Maintenant : 24 poses') if frame<240 else ('Avant : vol fixe','Maintenant : 8 poses')
            screen.blit(font.render(title1,True,(246,236,210)),(140,12))
            screen.blit(font.render(title2,True,(246,236,210)),(530,12))
            image=old[int(frame/60*12)%4 if frame<240 else 6]
            screen.blit(image,image.get_rect(midbottom=(230,400)))
            px,py=pose.pivot
            screen.blit(scaled[id(pose)],(650-px*3,400-py*3))
            if frame in (0,6,12,18,240):pg.image.save(screen,str(output/f'hero-preview-{frame}.png'))
            process.stdin.write(pg.image.tostring(screen,'RGB'))
        process.stdin.close();process.stdin=None
        _,errors=process.communicate()
        if process.returncode:raise RuntimeError(errors.decode('utf-8','replace'))
    finally:
        if process.poll() is None:process.kill();process.wait()
        game.close()
    print(output/'hero-course-compare.mp4')


if __name__=='__main__':export()
