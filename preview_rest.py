"""Export the real six-second idle, seated wait and input-driven stand-up."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import subprocess
import pygame as pg
from main import Game, STEP, ROOT


def export():
    import imageio_ffmpeg
    game=Game(True);game.state='play';output=ROOT/'output';output.mkdir(exist_ok=True)
    font=pg.font.SysFont('Segoe UI',21)
    images={id(p):tuple(pg.transform.scale(im,(240,240)) for im in p.images)
            for clip in game.animation_bank.clips.values() for p in clip}
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
             '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
             '-crf','18','-pix_fmt','yuv420p',str(output/'hero-rest-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for frame in range(600):
            for step in range(2):
                game.time+=STEP
                game.update(STEP,1 if frame>=550 else 0,frame==480,frame==480 and step==0,
                            activity=frame==480 and step==0)
            game.draw(1)
            if frame==450:pg.image.save(game.capture(),output/'hero-rest-game.png')
            screen=pg.transform.smoothscale(game.capture(),(960,540))
            pg.draw.rect(screen,(25,39,47),(630,125,310,310))
            pg.draw.line(screen,(205,169,100),(640,400),(930,400),2)
            screen.blit(font.render('Detail de l animation',True,(240,220,170)),(650,136))
            pose=game.hero_animation.sample(game.animation_bank);facing=game.hero_animation.render_facing()
            px,py=pose.pivot
            if facing<0:px=119-px
            screen.blit(images[id(pose)][0 if facing>0 else 1],(795-px*2,400-py*2))
            pg.draw.rect(screen,(17,30,36),(0,506,960,34))
            if frame<360:label=f'Inactivite : {frame/60:.1f} / 6 secondes'
            elif frame<480:label='Le heros s assoit en tailleur puis attend une commande'
            else:label='A le fait seulement se relever, sans saut ; puis nouvelle commande'
            screen.blit(font.render(label,True,(255,227,153)),(20,511))
            process.stdin.write(pg.image.tobytes(screen,'RGB'))
        process.stdin.close();error=process.stderr.read().decode(errors='replace');process.wait()
        if process.returncode:raise RuntimeError(error)
        assert game.hero.x>200 and not game.rest.active
    finally:
        if process.poll() is None:process.kill();process.wait()
        game.close()


if __name__=='__main__':export()
