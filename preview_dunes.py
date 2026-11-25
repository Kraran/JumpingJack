"""Menu cheat followed by a continuous native-HD walk across a high dune."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP,VIEW_W
from terrain import sand_height


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json');writer=None
        game.sound_on=False
        try:
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                     '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                     '-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'dunes-lv02-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            font=pg.font.SysFont('Segoe UI',18);max_error=0.;ungrounded=0;uploads=0
            for frame in range(480):
                pg.event.pump()
                if frame in (20,30,40,50):
                    character='LV02'[(frame-20)//10]
                    game.menu_key(pg.key.key_code(character.lower()),character)
                if frame==90:
                    game.hero=Hero(4350,sand_height(4350));game.hero.grounded=True
                    game.invuln=100;game.hero_animation.reset()
                axis=(1 if frame<360 else -1) if frame>=90 else 0
                for _ in range(2):
                    game.time+=STEP
                    if game.state=='play':game.update(STEP,axis,False,False)
                    if frame>=90:
                        max_error=max(max_error,abs(game.hero.y-sand_height(game.hero.x)))
                        ungrounded+=not game.hero.grounded
                if game.state=='play':
                    game.cam=game.prev_cam=max(0,min(game.world_length-VIEW_W,game.hero.x-500))
                protection=game.invuln;game.invuln=0;before=game.native_canvas.uploads
                try:game.draw(.5)
                finally:game.invuln=protection
                uploads+=game.native_canvas.uploads-before
                full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
                if frame==300:pg.image.save(full,ROOT/'output'/'dunes-walking.png')
                pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                label='LV02 dans le menu : départ direct au niveau 2' if frame<90 else 'Dunes irrégulières : montées et descentes continues, sans rebond'
                screen.blit(font.render(label,True,(255,227,153)),(18,511))
                writer.stdin.write(pg.image.tobytes(screen,'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert game.level_id==2 and game.lives==3
            assert max_error<1e-6 and ungrounded==0,(max_error,ungrounded)
            (ROOT/'output'/'dunes-validation.json').write_text(json.dumps({
                'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                'cheat':'LV02','level':game.level_id,'lives':game.lives,
                'max_foot_height_error':max_error,'ungrounded_steps':ungrounded,
                'new_texture_uploads_during_draw':uploads,
                'scope':'Native rendering and actual walking physics; protected from enemies for the demonstration.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
