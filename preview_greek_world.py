"""Campaign footage for all four Greek levels, with native GPU validation."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP,VIEW_W
from greece_levels import LEVELS


def preview(native=False,video=False):
    output=ROOT/'output';output.mkdir(exist_ok=True)
    writer=None
    with tempfile.TemporaryDirectory(prefix='jumpingjack-world2-') as directory:
        temporary=Path(directory)
        game=Game(not native,fullscreen=False,settings_path=temporary/'settings.json',saves_path=temporary/'saves')
        try:
            if video:
                import imageio_ffmpeg
                writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error',
                    '-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','60','-i','-',
                    '-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
                    str(output/'greece-world-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            observations=[]
            for level_id,start in ((5,600),(6,7000),(7,6250),(8,13000)):
                config=LEVELS[level_id];game.start_level(level_id);game.state='play';game.sound_on=False
                game.hero=Hero(start,config.floor_height(start));game.hero.grounded=True
                game.cam=game.prev_cam=max(0,min(config.LENGTH-VIEW_W,start-480))
                if level_id==8:game.cam_y=game.prev_cam_y=config.floor_height(start)-620
                game.invuln=100
                game.draw(1,present=False)
                # Include shadow rounding variants before measuring texture uploads.
                game.native_canvas.preload(list(game.native_canvas.primitives.values()))
                uploads=game.native_canvas.uploads
                for frame in range(180):
                    for event in pg.event.get():
                        if event.type==pg.QUIT:raise KeyboardInterrupt('Preview cancelled')
                    for _ in range(2):
                        h=game.hero
                        support=next((p for p in game.platforms if p.ground and p.kind!='greek_ceiling'
                                      and abs(h.y-p.y)<1 and p.x<=h.x<=p.x+p.w),None)
                        jump=bool(h.grounded and support and h.x>support.x+support.w-65)
                        game.time+=STEP;game.update(STEP,1,False,jump)
                    protection=game.invuln;game.invuln=0
                    try:game.draw(.5,present=native)
                    finally:game.invuln=protection
                    if frame==100:pg.image.save(game.capture(),output/f'greece-level{level_id:02}.png')
                    if writer:writer.stdin.write(pg.image.tobytes(game.capture(),'RGB'))
                new_uploads=game.native_canvas.uploads-uploads
                observations.append({'level':level_id,'title':config.TITLE,'platforms':len(game.platforms),
                    'crystals':len(game.gems),'deaths':game.deaths,'new_texture_uploads':new_uploads})
            if writer:
                writer.stdin.close();errors=writer.stderr.read().decode(errors='replace');writer.wait()
                if writer.returncode:raise RuntimeError(errors)
            report={'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,'frames':720,
                    'resident_textures':len(game.native_canvas.textures),
                    'scope':'Controlled gameplay shots with enemy protection; not a full combat replay.',
                    'levels':observations}
            (output/'greece-world-render-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False,indent=2))
            assert all(not o['deaths'] and not o['new_texture_uploads'] for o in observations),report
            if native:assert game.native_canvas.gpu,'GPU renderer unavailable'
        finally:
            if writer and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    parser.add_argument('--video',action='store_true');args=parser.parse_args()
    preview(args.native_check,args.video)
