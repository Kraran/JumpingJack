"""Show actual fall/glide contacts on ground and one-way platforms at 60 FPS."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import subprocess
import pygame as pg
from main import Hero, Platform, STEP, ROOT
from hero_animation import HeroAnimator, load_bank


def export():
    import imageio_ffmpeg  # optional developer dependency
    pg.init();pg.display.set_mode((64,64))
    bank=load_bank(ROOT/'assets')
    output=ROOT/'output';output.mkdir(exist_ok=True)
    screen=pg.Surface((960,600));font=pg.font.SysFont('Segoe UI',23)
    images={id(p):tuple(pg.transform.scale(im,(180,180)) for im in p.images)
            for clip in bank.clips.values() for p in clip}
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
             '-pix_fmt','rgb24','-s','960x600','-r','60','-i','-','-an',
             '-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(output/'hero-landing-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for frame in range(240):
            if frame%120==0:
                cases=[]
                for gliding in (False,True):
                    for ground in (True,False):
                        hero=Hero(500,525)
                        cases.append((hero,HeroAnimator(),gliding,ground,
                                      [Platform(400,620,200,100 if ground else 32,ground)]))
            screen.fill((25,39,47))
            for i,(hero,animation,gliding,ground,platforms) in enumerate(cases):
                for _ in range(2):
                    was_grounded=hero.grounded
                    hero.update(STEP,0,gliding,False,platforms)
                    animation.update(STEP,hero,was_grounded)
                left,top=(i%2)*480,(i//2)*300
                root_x=left+260;root_y=top+280+round((hero.y-620)*.85)
                floor_y=top+280
                pg.draw.rect(screen,(157,126,79),(left+45,floor_y,390,20 if ground else 9))
                label=('Vol plane' if gliding else 'Chute')+' / '+('sol' if ground else 'plateforme')
                screen.blit(font.render(label,True,(237,214,166)),(left+25,top+10))
                pose=animation.sample(bank)
                px,py=pose.pivot
                screen.blit(images[id(pose)][0],(root_x-round(px*1.5),root_y-round(py*1.5)))
            hero,animation,*_=cases[0]
            if animation.state=='land' and animation.sample(bank) is bank.clips['land'][3]:
                pg.image.save(screen,output/'hero-landing-preview.png')
            process.stdin.write(pg.image.tobytes(screen,'RGB'))
        process.stdin.close()
        error=process.stderr.read().decode(errors='replace');process.wait()
        if process.returncode:raise RuntimeError(error)
    finally:
        if process.poll() is None:process.kill();process.wait()
        pg.quit()


if __name__=='__main__':export()
