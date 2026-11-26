"""Isolated art preview: approved Gyrosphere, +10% size and reversible rotation."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import bisect
import json
import math
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import pygame as pg
from main import Game,Hero,ROOT
from tower_level import BASE_Y

DIAMETER=44  # Native HD pixels; previous concept target was 40.
FRAMES=120


def load_rotation():
    sheet=pg.image.load(str(ROOT/'assets'/'gyrosphere-preview-v1.png')).convert_alpha()
    # Find whole spheres across the sheet, avoiding authored gutter offsets.
    components=pg.mask.from_surface(sheet,96).connected_components(5000)
    components.sort(key=lambda mask:(mask.get_bounding_rects()[0].centery//256,
                                     mask.get_bounding_rects()[0].centerx))
    if len(components)!=24:raise ValueError(f'24 sphères attendues, trouvé {len(components)}')
    authored=[]
    for mask in components:
        rect=mask.get_bounding_rects()[0];cell=sheet.subsurface(rect).copy()
        alpha=mask.to_surface(surface=pg.Surface(sheet.get_size(),pg.SRCALPHA),
            setcolor=(255,255,255,255),unsetcolor=(255,255,255,0)).subsurface(rect)
        cell.blit(alpha,(0,0),special_flags=pg.BLEND_RGBA_MULT)
        authored.append(pg.transform.smoothscale(cell,(256,256)))
    # Allocate less time to near-duplicate authored angles, so the shell does
    # not seem to pause as its front lens passes the camera.
    probes=[]
    for frame in authored:
        image=pg.transform.smoothscale(frame,(64,64))
        rgb=pg.surfarray.array3d(image).astype(np.float32)
        opacity=pg.surfarray.array_alpha(image).astype(np.float32)/255
        probes.append(rgb*opacity[...,None])
    distances=[float(np.sqrt(np.mean((probes[(i+1)%24]-probes[i])**2))) for i in range(24)]
    floor=sum(distances)/len(distances)*.12
    cumulative=[0.]
    for distance in distances:cumulative.append(cumulative[-1]+max(floor,distance))
    frames=[]
    for i in range(FRAMES):
        phase=i/FRAMES*cumulative[-1];lo=min(23,bisect.bisect_right(cumulative,phase)-1)
        weight=(phase-cumulative[lo])/(cumulative[lo+1]-cumulative[lo])
        image=authored[lo].copy();other=authored[(lo+1)%24].copy()
        image.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
        other.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
        image.blit(other,(0,0),special_flags=pg.BLEND_RGBA_ADD)
        frames.append(image)
    return frames


def export():
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as folder:
        game=Game(True,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        writer=None
        try:
            frames=load_rotation()
            small=[pg.transform.smoothscale(frame,(DIAMETER,DIAMETER)) for frame in frames]
            large=[pg.transform.smoothscale(frame,(360,360)) for frame in frames]
            game.start_level(4);game.state='play';game.invuln=0
            game.hero=Hero(400,BASE_Y);game.hero.grounded=True
            game.cam_y=game.prev_cam_y=14400-720
            title=pg.font.SysFont('Segoe UI',32)
            font=pg.font.SysFont('Segoe UI',23)
            panel=pg.Surface((510,590),pg.SRCALPHA);panel.fill((13,23,30,235))
            glow=pg.Surface((70,70),pg.SRCALPHA)
            for radius in range(34,0,-1):
                pg.draw.circle(glow,(20,190,215,round(12*(1-radius/35))),(35,35),radius)
            writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-crf','17','-pix_fmt','yuv420p',
                str(ROOT/'output'/'gyrosphere-animation-preview.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            selected=set();directions=set()
            for i in range(600):
                t=i/60;travel=90*math.sin(math.tau*t/10)
                angle=travel/(DIAMETER/1.5*math.pi)
                index=round(angle*FRAMES)%FRAMES;selected.add(index)
                direction=1 if math.cos(math.tau*t/10)>=0 else -1;directions.add(direction)
                game.elapsed=game.previous_elapsed=t;game.time=t
                game.draw(1,present=False);image=game.capture()
                px=round((700+travel)*1.5)
                py=round((BASE_Y-85+2*math.sin(t*math.tau/4)-game.cam_y)*1.5)
                image.blit(glow,(px-35,py-35));image.blit(small[index],(px-DIAMETER//2,py-DIAMETER//2))
                image.blit(panel,(45,220))
                image.blit(title.render('GYROSPHÈRE',True,(231,204,144)),(80,250))
                image.blit(font.render('Gros plan de la rotation',True,(200,219,221)),(80,300))
                image.blit(large[index],(120,350))
                image.blit(font.render('Taille légèrement augmentée : +10 %',True,(220,234,233)),(80,745))
                image.blit(font.render('Déplacement vers la droite' if direction>0 else 'Déplacement vers la gauche',True,(94,222,236)),(80,780))
                output=pg.transform.smoothscale(image,(1280,720))
                if i==90:pg.image.save(output,ROOT/'output'/'gyrosphere-animation-preview.png')
                writer.stdin.write(pg.image.tobytes(output,'RGB'))
            writer.stdin.close();error=writer.stderr.read().decode();code=writer.wait();writer=None
            if code:raise RuntimeError(error)
            assert directions=={-1,1} and len(selected)>100
            report=dict(authored_poses=24,prepared_poses=FRAMES,sampled_poses=len(selected),diameter_native=DIAMETER,
                        increase_percent=10,duration_seconds=10,fps=60,rotation_reversed=True,isolated_preview=True)
            (ROOT/'output'/'gyrosphere-preview-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:
            if writer:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':export()
