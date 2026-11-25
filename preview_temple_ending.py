"""Native approach, back-facing stair climb, fade and level-03 completion."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP,VIEW_W
import temple_level as temple


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        g=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            g.start_level(3);g.state='play';g.sound_on=False;g.invuln=2
            g.hero=Hero(14000,620);g.hero.grounded=True
            g.cam=g.prev_cam=temple.LENGTH-VIEW_W
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'temple-ending-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0;captures=set();poses=set();font=pg.font.SysFont('Segoe UI',18)
            for frame in range(360):
                pg.event.pump()
                for _ in range(2):
                    g.time+=STEP
                    if g.state=='play':g.update(STEP,1,False,False)
                protection=g.invuln;g.invuln=0;before=g.native_canvas.uploads
                try:g.draw(1)
                finally:g.invuln=protection
                if g.state=='play':uploads+=g.native_canvas.uploads-before
                image=g.capture();elapsed=g.temple_exit.elapsed
                for name,at in (('entrance',.1),('turn',.63),('climb',1.65),('darkness',3.2)):
                    if g.temple_exit.active and elapsed>=at and name not in captures:
                        pg.image.save(image,ROOT/'output'/f'temple-ending-{name}.png');captures.add(name)
                if elapsed>=.45:poses.add(round((elapsed-.45)*120))
                image=pg.transform.smoothscale(image,(1280,720));pg.draw.rect(image,(12,26,33),(0,680,1280,40))
                label='Le sanctuaire · le héros monte les marches et disparaît dans le noir'
                image.blit(font.render(label,True,(245,217,160)),(18,688));writer.stdin.write(pg.image.tobytes(image,'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert g.state=='win' and g.lives==3 and len(captures)==4
            (ROOT/'output'/'temple-ending-validation.json').write_text(json.dumps({'gpu':g.native_canvas.gpu,
                'renderer':g.presentation.renderer,'new_gameplay_texture_uploads':uploads,'ending_duration':g.temple_exit.elapsed,
                'state':g.state,'lives':g.lives,'poses_seen':len(poses),'ending_atlas':g.temple_exit_sprites.atlas.get_size()},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
