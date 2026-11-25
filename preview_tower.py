"""Controlled cuts of real ascent at the bottom, checkpoint and summit."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,ROOT,STEP
import tower_level as tower


def controls(g,targets):
    source=g.hero.x
    for target in targets:
        for _ in range(120):
            h=g.hero;error=source-(h.x+h.vx*abs(h.vx)/4800)
            yield 1 if error>2 else -1 if error<-2 else 0,False
            if abs(g.hero.x-source)<4 and abs(g.hero.vx)<8 and g.hero.recovery<=0:break
        center=target.x+target.w/2
        for tick in range(260):
            h=g.hero;error=center-(h.x+h.vx*abs(h.vx)/3500)
            yield 1 if error>2 else -1 if error<-2 else 0,tick==0
            if g.hero.grounded and abs(g.hero.y-target.y)<1:break
        else:raise AssertionError('Preview missed a platform')
        source=center


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        g=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json',saves_path=Path(directory)/'saves')
        writer=None
        try:
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                str(ROOT/'output'/'tower-level-demo.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            uploads=0;sections=[];font=pg.font.SysFont('Segoe UI',16)
            for name,source_index,indices in (('base',None,range(4)),('guard',20,range(21,24)),
                    ('checkpoint',63,range(64,67)),('summit',len(tower.LEDGES)-3,range(len(tower.LEDGES)-2,len(tower.LEDGES)+1))):
                g.start_level(4);g.state='play';g.sound_on=False;g.invuln=100
                route=tower.route_platforms(g.platforms)
                if source_index is None:x,y=tower.START
                else:p=route[source_index];x,y=p.x+p.w/2,p.y
                g.hero=Hero(x,y);g.hero.grounded=True;g.hero_animation.reset()
                g.cam_y=g.prev_cam_y=(tower.HEIGHT-720 if source_index is None else tower.camera_target(y))
                action=iter(controls(g,[route[i] for i in indices]));finished=False;frame=0;hold=0
                while not finished or hold<45:
                    pg.event.pump()
                    for _ in range(2):
                        g.time+=STEP
                        if not finished and g.state=='play':
                            try:axis,pressed=next(action)
                            except StopIteration:finished=True;axis=0;pressed=False
                            g.update(STEP,axis,False,pressed)
                        else:finished=True
                    if finished:hold+=1
                    before=g.native_canvas.uploads;protection=g.invuln;g.invuln=0
                    try:g.draw(1)
                    finally:g.invuln=protection
                    if g.state=='play':uploads+=g.native_canvas.uploads-before
                    image=g.capture()
                    if frame==50:pg.image.save(image,ROOT/'output'/f'tower-{name}.png')
                    image=pg.transform.smoothscale(image,(960,540));pg.draw.rect(image,(12,26,33),(0,512,960,28))
                    image.blit(font.render('Niveau 04 · la tour · ascension réelle, passages sélectionnés',True,(245,217,160)),(12,517))
                    writer.stdin.write(pg.image.tobytes(image,'RGB'));frame+=1
                    if frame>700:raise AssertionError('Preview did not finish')
                sections.append({'section':name,'hero':[g.hero.x,g.hero.y],'checkpoint':g.check_index,'state':g.state})
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert g.state=='win' and g.lives==3 and g.cam==0
            (ROOT/'output'/'tower-render-validation.json').write_text(json.dumps({'gpu':g.native_canvas.gpu,
                'renderer':g.presentation.renderer,'new_gameplay_texture_uploads':uploads,'horizontal_camera':g.cam,
                'height':tower.HEIGHT,'width':tower.WIDTH,'sections':sections,
                'scope':'Controlled cuts with real jumps and temporary enemy protection; full route verified separately.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            g.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
