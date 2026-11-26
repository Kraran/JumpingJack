"""Native screenshots of the royal header in four levels and long translations."""
import json
from pathlib import Path
import tempfile
import pygame as pg
from main import Game,ROOT


def preview():
    with tempfile.TemporaryDirectory() as folder:
        g=Game(False,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False;cases=[]
            for level,language in ((1,'fr'),(2,'de'),(3,'ru'),(4,'fr')):
                g.new_game();g.start_level(level);g.set_language(language);g.state='play'
                g.score=12340;g.taken=set(range(18));g.medallions.count=1
                g.lives=6 if level==3 else 3
                if level in (2,3):g.energy.reset(0);g.energy.warning=.7;g.extra_life_notice=2.
                if level==4:g.notice=2.
                g.draw(1)
                pg.image.save(g.capture(),ROOT/'output'/f'royal-hud-level{level}-{language}.png')
                cases.append(dict(level=level,language=language,lives=g.lives))
            before=g.native_canvas.uploads
            g.draw(1)
            report=dict(gpu=g.native_canvas.gpu,new_repeated_frame_uploads=g.native_canvas.uploads-before,cases=cases)
            (ROOT/'output'/'royal-hud-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:g.close()


if __name__=='__main__':preview()
