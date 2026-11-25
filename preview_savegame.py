"""Native walkthrough of private temporary save slots and menu navigation."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP
from savegame import capture
from terrain import sand_height


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            for index,(level,x,lives) in enumerate(((1,800,3),(1,4740,2),(2,9540,2))):
                game.start_level(level);game.hero=Hero(x,sand_height(x) if level==2 else 620)
                game.hero.grounded=True;game.lives=lives;game.elapsed=(index+1)*143.5
                game.cam=max(0,x-500);game.taken=set(range(index*5+3));game.energy.value=100-index*18
                game.medallions.count=int(level==2);game.medallions.claimed_levels={1} if level==2 else set()
                game.saves.write(index,capture(game))
            game.new_game();game.state='title';game.sound_on=False
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                     '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                     '-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'savegame-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0
            for frame in range(300):
                pg.event.pump()
                if frame==30:game.menu.selected['title']=2;game.menu_action('activate')
                if frame==90:
                    game.menu.selected['load']=2;game.menu_action('activate')
                    assert game.state=='play' and game.level_id==2 and game.lives==2
                if frame==125:game.enter_menu('pause')
                if frame==155:game.menu.selected['pause']=2;game.menu_action('activate')
                if frame==200:game.menu.selected['save']=3;game.menu_action('activate')
                if frame==230:game.menu_action('activate')
                if frame==270:game.menu_action('back')
                for _ in range(2):
                    game.time+=STEP
                    if game.state=='play':game.update(STEP,0,False,False)
                before=game.native_canvas.uploads;game.draw(1)
                if game.state=='play':uploads+=game.native_canvas.uploads-before
                image=game.capture()
                for at,name in ((15,'title'),(60,'load'),(140,'pause'),(215,'save'),(250,'overwrite')):
                    if frame==at:pg.image.save(image,ROOT/'output'/f'savegame-{name}.png')
                writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert game.saves.read(3).status=='ready' and game.saves.read(4).status=='empty'
            (ROOT/'output'/'savegame-validation.json').write_text(json.dumps({
                'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                'new_texture_uploads_during_gameplay':uploads,'slots':5,'loaded_level':game.level_id,
                'lives':game.lives,'statuses':[slot.status for slot in game.saves.list()],
                'scope':'Real disk writes in a temporary directory; title/load/play/pause/save/overwrite/back.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
