"""Real guardian dive, dodge, pull-up and solar destruction on the native GPU."""
import argparse
import json
import subprocess
import pygame as pg
from main import Game,Hero,STEP,ROOT


def preview(native=False):
    import imageio_ffmpeg
    game=Game(not native,fullscreen=False);output=ROOT/'output';writer=None;results=[];seen=set()
    try:
        game.sound_on=False
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                 '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                 '-crf','18','-pix_fmt','yuv420p',str(output/'solar-guardian-demo.mp4')]
        writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        font=pg.font.SysFont('Segoe UI',18)
        for stage,frames in ((0,120),(1,240),(2,120)):
            game.reset();game.state='play';game.invuln=0
            game.dead_beetles=set(range(6));game.cam=game.prev_cam=8320
            game.hero=Hero(9100 if stage==2 else 9300,620);game.hero.grounded=True
            guardian=game.vultures[2];game.vultures=[guardian]
            if stage==2:
                guardian.x=guardian.px=9320;guardian.y=guardian.py=566
                guardian.vx=guardian.vy=0;guardian.facing=-1
                guardian.target=(9100,593);guardian.change('warning')
            for frame in range(frames):
                pg.event.pump()
                for step in range(2):
                    game.time+=STEP
                    axis=-1 if stage==1 and 25<=frame<80 else 0
                    game.update(STEP,axis,False,False,fire=stage==2 and frame==6 and step==0)
                game.draw(.5);seen.add(guardian.sample())
                full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
                key=guardian.sample(.5);area=game.vulture_sprites.areas[key]
                detail=game.vulture_sprites.atlas.subsurface(area)
                pg.draw.rect(screen,(25,39,47),(20,90,300,290))
                screen.blit(detail,(42,115))
                pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                labels=('Gardien solaire : repérage et piqué mortel','Esquive : la cible du piqué reste fixe, puis remontée','Rayon solaire : métal, flammes et fumée')
                screen.blit(font.render(labels[stage],True,(255,227,153)),(18,511))
                if stage==1 and frame==40:
                    pg.image.save(full,output/'solar-guardian-game.png')
                    pg.image.save(screen,output/'solar-guardian-preview.png')
                writer.stdin.write(pg.image.tobytes(screen,'RGB'))
            results.append((game.deaths,guardian.alive))
        writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
        if writer.returncode:raise RuntimeError(error)
        assert results[0][0]==1,results
        assert results[1][0]==0,results
        assert results[2]==(0,False),results
        (output/'solar-guardian-validation.json').write_text(json.dumps({
            'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
            'stage_deaths_alive':results,'authored_poses':72,'cached_variants':len(game.vulture_sprites.areas),
            'observed_animation_states':sorted({key[0] for key in seen}),
            'atlas_size':list(game.vulture_sprites.atlas.get_size()),
            'atlas_cached':id(game.vulture_sprites.atlas) in game.native_canvas.textures if game.native_canvas.gpu else None},indent=2),encoding='utf-8')
    finally:
        if writer is not None and writer.poll() is None:writer.kill();writer.wait()
        game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
