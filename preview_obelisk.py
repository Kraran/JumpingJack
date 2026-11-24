"""Checkpoint activation and permanent crackle, using the actual game renderer."""
import argparse
import json
import subprocess
import pygame as pg
from main import Game,Hero,STEP,ROOT
from obelisk import CHECKPOINT_X,GROUND_Y,RESPAWN


def preview(native=False):
    import imageio_ffmpeg
    game=Game(not native,fullscreen=False);output=ROOT/'output';output.mkdir(exist_ok=True)
    writer=None
    try:
        game.state='play';game.sound_on=False;game.invuln=100
        game.hero=Hero(CHECKPOINT_X-90,GROUND_Y);game.hero.grounded=True
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                 '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                 '-crf','18','-pix_fmt','yuv420p',str(output/'obelisk-demo.mp4')]
        writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        font=pg.font.SysFont('Segoe UI',19)
        for frame in range(300):
            pg.event.pump()
            for _ in range(2):
                game.time+=STEP
                game.update(STEP,1 if 30<=frame<41 else 0,False,False)
            game.cam=game.prev_cam=CHECKPOINT_X-640;game.draw(.5)
            full=game.capture()
            if frame in (20,70,180):pg.image.save(full,output/f'obelisk-{frame}.png')
            screen=pg.transform.smoothscale(full,(960,540))
            # Magnified detail preserves the actual composited scene and lighting.
            detail=pg.transform.scale(full.subsurface((870,710,180,240)),(225,300))
            screen.blit(detail,(700,95));pg.draw.rect(screen,(223,186,102),(699,94,227,302),1)
            pg.draw.rect(screen,(17,30,36),(0,506,960,34))
            label='Obélisque inactif' if not game.obelisk.active else ('Activation : lumière ascendante' if game.obelisk.clock<1.2 else 'Point de reprise actif : crépitement permanent')
            screen.blit(font.render(label,True,(255,227,153)),(18,511))
            writer.stdin.write(pg.image.tobytes(screen,'RGB'))
        writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
        if writer.returncode:raise RuntimeError(error)
        assert game.obelisk.active and game.checkpoint==RESPAWN
        (output/'obelisk-validation.json').write_text(json.dumps({
            'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
            'single_checkpoint_x':CHECKPOINT_X,'respawn':RESPAWN,
            'activation_complete':game.obelisk.clock>1.2,'frames':300,
            'cached_obelisk_textures':len(game.obelisk_sprites.images)},indent=2),encoding='utf-8')
    finally:
        if writer is not None and writer.poll() is None:writer.kill();writer.wait()
        game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
