"""GPU demonstration of Horus plasma, fast shot debits and crystal refill."""
import json
from pathlib import Path
import subprocess
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP


def preview():
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as folder:
        g=Game(False,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        writer=None
        try:
            g.new_game();g.state='play';g.sound_on=False;g.gamepads.rumble_enabled=False
            g.hero=Hero(1700,620);g.hero.grounded=True;g.cam=g.prev_cam=1200.
            g.energy.reset(70)
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'solar-gauge-horus-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for frame in range(300):
                pg.event.pump()
                if frame in (65,110):g.energy.spend_ray()
                if frame==150:g.energy.value=0.
                if frame==210:
                    for _ in range(5):g.energy.collect()
                for _ in range(2):
                    g.previous_elapsed=g.elapsed;g.elapsed+=STEP;g.energy.update_display(STEP)
                g.draw(1);image=g.capture()
                if frame in (35,135,195):
                    label={35:'full',135:'low',195:'empty'}[frame]
                    pg.image.save(image,ROOT/'output'/f'solar-gauge-horus-{label}.png')
                writer.stdin.write(pg.image.tobytes(pg.transform.smoothscale(image,(960,540)),'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            before=g.native_canvas.uploads
            for i in range(96):
                for low in (False,True):g.solar_gauge.draw(g.canvas,.6,i/60,low)
            report=dict(gpu=g.native_canvas.gpu,frames=96,new_animation_texture_uploads=g.native_canvas.uploads-before,
                        final_energy=g.energy.value,window=list(g.solar_gauge.window))
            (ROOT/'output'/'solar-gauge-horus-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:
            if writer:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':preview()
