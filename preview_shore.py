"""Native walkthrough of both tapered Nile banks and their animated contact."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,STEP,ROOT
from terrain import sand_height


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json');writer=None
        try:
            game.start_level(2);game.state='play';game.sound_on=False;game.invuln=100
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                     '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                     '-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'shore-transition-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            font=pg.font.SysFont('Segoe UI',18);uploads=0;frames=set()
            for name,camera,x in (('left',260,600),('right',2700,3670)):
                game.hero=Hero(x,sand_height(x));game.hero.grounded=True
                game.hero_animation.reset();game.rest.reset()
                for frame in range(180):
                    pg.event.pump()
                    for _ in range(2):game.time+=STEP;game.update(STEP,0,False,False)
                    game.cam=game.prev_cam=camera
                    protection=game.invuln;game.invuln=0;before=game.native_canvas.uploads
                    try:game.draw(.5)
                    finally:game.invuln=protection
                    uploads+=game.native_canvas.uploads-before
                    frames.add(int((game.elapsed/2.4%1)*48))
                    full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
                    if frame==90:pg.image.save(full,ROOT/'output'/f'shore-{name}.png')
                    pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                    screen.blit(font.render('Berges en pente · sable humide · reflets et remous discrets',True,(255,227,153)),(18,511))
                    writer.stdin.write(pg.image.tobytes(screen,'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert game.lives==3 and len(frames)==48
            (ROOT/'output'/'shore-validation.json').write_text(json.dumps({
                'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                'new_texture_uploads_during_draw':uploads,'shore_frames_seen':len(frames),
                'banks':[700,3140],'bank_contact_height':640,'lives':game.lives,
                'scope':'Both banks rendered with real simulation, protected from enemies for the demonstration.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
