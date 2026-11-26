"""Capture the real GPU-rendered end-of-level life bonus countdown."""
import json
from pathlib import Path
import subprocess
import tempfile
import pygame as pg
from main import Game,Hero,ROOT


def preview():
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as folder:
        g=Game(False,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        writer=None
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False;g.settings.language='fr'
            g.new_game();g.hero=Hero(9630,620);g.cam=g.prev_cam=8320.
            g.award_points(2340);g.complete_level();started=g.time
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'level-life-bonus-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for frame in range(210):
                pg.event.pump();g.time=started+frame/60;g.draw(1)
                image=g.capture()
                if frame==60:pg.image.save(image,ROOT/'output'/'level-life-bonus-counting.png')
                if frame==170:pg.image.save(image,ROOT/'output'/'level-life-bonus-finished.png')
                writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            report=dict(gpu=g.native_canvas.gpu,lives=g.lives,score=g.score,life_bonus=g.victory_lives*100)
            (ROOT/'output'/'level-life-bonus-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':preview()
