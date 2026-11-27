"""Exercise actual F12 events and PNG files on the native GPU, including bezels."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame as pg
from main import Game,ROOT
from settings import Settings


def verify():
    captures=[]
    with tempfile.TemporaryDirectory(prefix='jumpingjack-f12-') as directory:
        temp=Path(directory);settings=temp/'settings.json'
        Settings(fullscreen=False,music=False).save(settings)
        game=Game(False,fullscreen=False,settings_path=settings,saves_path=temp/'saves')
        try:
            assert game.native_canvas.gpu
            game.sdl_window.hide();game.start_level(5)
            for state,resolution in (('play',(2560,1080)),('title',(3840,1080))):
                game.sdl_window.size=resolution;pg.event.pump();pg.event.clear()
                game.state=state;game.acc=0.
                pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_F12))
                with patch.object(game,'close'):game.run(frames=2)
                game.screenshots.close()
                assert game.screenshots.error is None,game.screenshots.error
                path=game.screenshots.last_path;image=pg.image.load(str(path))
                assert image.get_size()==resolution,(image.get_size(),resolution)
                assert image.get_at((100,500))[:3]!=(10,17,22),'Missing bezel'
                assert path.parent==ROOT/'captures'
                captures.append({'state':state,'size':image.get_size(),'file':path.name,'bytes':path.stat().st_size})
            assert len({item['file'] for item in captures})==2
            report={'gpu':True,'renderer':game.presentation.renderer,'trigger':'Actual F12 key events',
                    'captures':captures,'png_reopened':True,'async_writes_completed_before_close':True,
                    'user_preferences_and_saves':'temporary data only'}
            (ROOT/'output/screenshot-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report,indent=2))
        finally:game.close()


if __name__=='__main__':verify()
