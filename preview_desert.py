"""Four controlled camera shots of level 02, using the real gameplay physics."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import pygame as pg
from main import Game,Hero,STEP,ROOT,VIEW_W
from desert_level import LENGTH,MEDALLION
from terrain import sand_height,surface_height


def preview(native=False):
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory() as directory:
        game=Game(not native,fullscreen=False,settings_path=Path(directory)/'settings.json')
        writer=None
        try:
            game.start_level(2);game.state='play';game.sound_on=False;game.invuln=100
            game.medallions.collect(1)
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                     '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                     '-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'desert-level-demo.mp4')]
            writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            shots=(('river',240,Hero(650,620)),('rocks',240,Hero(4350,sand_height(4350))),
                   ('pylon',150,Hero(9600,sand_height(9600))),('medallion',180,Hero(MEDALLION[0],455)))
            observations=[];uploads=0;font=pg.font.SysFont('Segoe UI',18)
            for name,frames,hero in shots:
                game.hero=hero;hero.grounded=True;hero.vx=340 if name in ('river','rocks') else 0
                game.hero_animation.reset();game.rest.reset()
                for frame in range(frames):
                    pg.event.pump()
                    for step in range(2):
                        game.time+=STEP
                        axis=1 if name in ('river','rocks') else 0
                        pressed=False
                        if axis and game.hero.grounded:
                            support=next((p for p in game.platforms if abs(game.hero.y-surface_height(p,game.hero.x))<1
                                          and p.x<=game.hero.x<=p.x+p.w),None)
                            pressed=support is not None and game.hero.x>=support.x+support.w-45
                        if name=='medallion':pressed=frame==45 and step==0
                        game.update(STEP,axis,False,pressed)
                    game.cam=game.prev_cam=max(0,min(LENGTH-VIEW_W,game.hero.x-500))
                    protection=game.invuln;game.invuln=0
                    before=game.native_canvas.uploads
                    try:game.draw(.5)
                    finally:game.invuln=protection
                    uploads+=game.native_canvas.uploads-before
                    full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
                    labels={'river':'Niveau 02 · Le Nil : cinq passerelles au-dessus de l’eau mortelle',
                            'rocks':'Le désert : dunes, temples ensablés et rochers solides',
                            'pylon':'Deux pylônes de reprise : lumière ascendante et crépitements',
                            'medallion':'Un médaillon en hauteur, à 90 % du parcours'}
                    pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                    screen.blit(font.render(labels[name],True,(255,227,153)),(18,511))
                    if frame==frames//2:
                        pg.image.save(full,ROOT/'output'/f'desert-{name}.png')
                        observations.append({'shot':name,'hero':[game.hero.x,game.hero.y],
                                             'lives':game.lives,'medallions':game.medallions.count})
                    writer.stdin.write(pg.image.tobytes(screen,'RGB'))
                assert game.lives==3,(name,game.deaths,game.hero.x,game.hero.y)
            writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
            if writer.returncode:raise RuntimeError(error)
            assert game.medallions.count==2
            (ROOT/'output'/'desert-render-validation.json').write_text(json.dumps({
                'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                'new_texture_uploads_during_draw':uploads,'world_length':LENGTH,
                'platforms':len(game.platforms),'crystals':len(game.gems),
                'medallion':MEDALLION,'checkpoints':[o.x for o in game.obelisks],
                'inventory_after_pickup':game.medallions.count,'shots':observations,
                'scope':'Controlled camera cuts and protection from enemies; real physics, deadly water, real pickups.'},indent=2),encoding='utf-8')
        finally:
            if writer is not None and writer.poll() is None:writer.kill();writer.wait()
            game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
