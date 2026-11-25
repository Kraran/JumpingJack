"""Native flame loop followed by an actual lethal contact in level 03."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        g=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            g.start_level(3);g.state='play';g.sound_on=False
            g.hero=Hero(550,620);g.hero.grounded=True;g.cam=g.prev_cam=0
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'temple-fire-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0;seen=set();font=pg.font.SysFont('Segoe UI',18)
            for frame in range(210):
                pg.event.pump()
                if frame<96:g.elapsed=(frame+.25)/60;g.time=g.elapsed
                else:
                    if frame==96:g.hero=Hero(550,365);g.hero.vx=240;g.invuln=0
                    for _ in range(2):g.time+=STEP;g.update(STEP,1 if g.deaths==0 else 0,False,False)
                g.cam=g.prev_cam=0
                seen.add(g.temple_art.flame_frame(g.elapsed))
                before=g.native_canvas.uploads;g.draw(1);uploads+=g.native_canvas.uploads-before
                image=g.capture()
                if frame==24:
                    pg.image.save(image,ROOT/'output'/'temple-fire-game.png')
                    pg.image.save(image.subsurface((890,405,175,320)),ROOT/'output'/'temple-fire-detail.png')
                image=pg.transform.smoothscale(image,(1280,720));pg.draw.rect(image,(12,26,33),(0,680,1280,40))
                label='Flammes réalistes · animation continue' if frame<96 else 'Contact avec les flammes · une vie perdue'
                image.blit(font.render(label,True,(245,217,160)),(18,688));writer.stdin.write(pg.image.tobytes(image,'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert g.deaths==1 and g.lives==2 and len(seen)==48
            (ROOT/'output'/'temple-fire-validation.json').write_text(json.dumps({'gpu':g.native_canvas.gpu,
                'renderer':g.presentation.renderer,'new_texture_uploads':uploads,'flame_frames_seen':len(seen),
                'deaths':g.deaths,'lives':g.lives,'scope':'Real temple flame loop and actual contact/respawn.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
