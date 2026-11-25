"""Compare legacy addition with color-preserving plasma on the real blue sky."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,STEP,ROOT
from plasma_fx import PlasmaEffect


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json');writer=None
        try:
            game.start_level(2);game.state='play';game.sound_on=False;game.invuln=100
            colored=game.solar.effect
            legacy=PlasmaEffect(pg.image.load(str(ROOT/'assets'/'solar-plasma.png')).convert())
            game.native_canvas.preload(legacy.images)
            uploads=game.native_canvas.uploads;font=pg.font.SysFont('Segoe UI',16);metrics=None
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                     '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                     '-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'solar-color-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for frame in range(180):
                pg.event.pump()
                if frame%60==0:
                    game.hero=Hero(5480,300);game.hero.vy=-160
                    game.hero_animation.reset();game.solar.reset();game.energy.refill()
                game.solar.effect=colored
                for step in range(2):
                    game.time+=STEP;game.update(STEP,0,False,False,fire=frame%60==0 and step==0)
                game.cam=game.prev_cam=5030
                protection=game.invuln;game.invuln=0;captures=[]
                try:
                    for effect in (legacy,colored):
                        game.solar.effect=effect;game.draw(1);captures.append(game.capture())
                finally:game.invuln=protection;game.solar.effect=colored
                screen=pg.Surface((960,540))
                for index,full in enumerate(captures):
                    band=pg.transform.smoothscale(full.subsurface((0,180,1920,540)),(960,270))
                    screen.blit(band,(0,index*270))
                    pg.draw.rect(screen,(17,30,36),(0,index*270,960,27))
                    label='AVANT · le rayon sature vers le blanc' if index==0 else 'APRÈS · filaments dorés et cœur lumineux'
                    screen.blit(font.render(label,True,(255,227,153)),(14,index*270+3))
                if frame==12:
                    pg.image.save(screen,ROOT/'output'/'solar-color-comparison.png')
                    pg.image.save(captures[1],ROOT/'output'/'solar-color-game.png')
                    start,y,end=game.solar.geometry(game.hero,game.platforms)
                    px,py=game.canvas.point((start-game.cam,y));right=game.canvas.point((end-game.cam,y))[0]
                    counts=[];golden=0
                    for index,full in enumerate(captures):
                        white=0
                        for x in range(px+40,min(right-15,1920)):
                            for row in range(py-25,py+26):
                                r,g,b,_=full.get_at((x,row))
                                white+=min(r,g,b)>248
                                if index:golden+=r>b+20 and r>g+5
                        counts.append(white)
                    metrics={'white_pixels_before':counts[0],'white_pixels_after':counts[1],
                             'gold_pixels_after':golden}
                writer.stdin.write(pg.image.tobytes(screen,'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert metrics['white_pixels_before']>100
            assert metrics['white_pixels_after']<metrics['white_pixels_before']*.1,metrics
            assert metrics['gold_pixels_after']>100
            (ROOT/'output'/'solar-color-validation.json').write_text(json.dumps({
                'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                'new_texture_uploads':game.native_canvas.uploads-uploads,
                'alpha_compositing':colored.alpha_blend,**metrics,
                'scope':'Same live game scene rendered with the legacy and corrected atlas; controlled repeated shots, protected from enemies.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
