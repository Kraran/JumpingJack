"""Native menu walkthrough: navigation, settings, fullscreen and pause."""
import argparse
import json
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path
import pygame as pg
from main import Game,STEP,ROOT
from gamepad import PadSnapshot
from settings import Settings


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        preferences=Path(directory)/'settings.json'
        game=Game(not native,fullscreen=False,settings_path=preferences);writer=None
        try:
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                     '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                     '-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'menu-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            captures={30:'title',110:'settings',145:'controls',188:'gameplay',215:'pause'}
            observations=[];fullscreen=[];lazy_uploads=0;rebuilds=0;upload_events=[]
            for frame in range(300):
                pg.event.pump()
                canvas=game.native_canvas
                if frame==45:game.menu_key(pg.K_DOWN);game.menu_key(pg.K_RETURN)
                if native and frame in (55,65):
                    game.menu_key(pg.K_RIGHT);fullscreen.append(game.fullscreen)
                if frame in (75,85,95):game.menu_key(pg.K_DOWN);game.menu_key(pg.K_RIGHT)
                if frame==125:game.menu_key(pg.K_DOWN);game.menu_key(pg.K_RETURN)
                if frame==160:game.menu_key(pg.K_ESCAPE)
                if frame==170:game.menu_key(pg.K_ESCAPE);game.menu_key(pg.K_UP);game.menu_key(pg.K_RETURN)
                if frame==200:game.handle_pad(PadSnapshot(start_pressed=True))
                if frame==230:game.menu_key(pg.K_DOWN);game.handle_pad(PadSnapshot(confirm_pressed=True))
                if frame==250:game.handle_pad(PadSnapshot(cancel_pressed=True))
                if frame==265:game.handle_pad(PadSnapshot(start_pressed=True))
                if frame==280:
                    game.handle_pad(PadSnapshot(start_pressed=True))
                    game.menu.selected['pause']=3;game.menu_key(pg.K_RETURN)
                if frame==299:
                    game.menu.selected['title']=3;game.menu_key(pg.K_RETURN)
                for _ in range(2):
                    game.time+=STEP
                    if game.state=='play':game.update(STEP,0,False,False)
                if canvas is not game.native_canvas:rebuilds+=1
                before=game.native_canvas.uploads
                game.draw(.5)
                extra=game.native_canvas.uploads-before;lazy_uploads+=extra
                if extra:upload_events.append({'frame':frame,'state':game.state,'count':extra})
                image=game.capture()
                if frame in captures:
                    name=captures[frame];pg.image.save(image,ROOT/'output'/f'menu-{name}.png')
                    observations.append({'frame':frame,'page':name,'state':game.state})
                screen=pg.transform.smoothscale(image,(960,540))
                writer.stdin.write(pg.image.tobytes(screen,'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            saved=Settings.load(preferences)
            assert (saved.sound,saved.rumble,saved.show_fps)==(False,False,True)
            assert game.quit_requested
            assert [item['state'] for item in observations]==['title','settings','controls','play','pause']
            (ROOT/'output'/'menu-validation.json').write_text(json.dumps({
                'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                'new_texture_uploads_during_draw':lazy_uploads,'texture_upload_events':upload_events,
                'renderer_rebuilds':rebuilds,'cached_textures':len(game.native_canvas.textures),
                'fullscreen_then_window':fullscreen,'saved_settings':asdict(saved),
                'quit_requested':game.quit_requested,'observations':observations},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
