"""Demonstrate the three lives, terminal death and controller restart."""
import argparse
import json
import subprocess
import pygame as pg
from main import Game,STEP,ROOT
from gamepad import PadSnapshot


def preview(native=False):
    import imageio_ffmpeg
    game=Game(not native,fullscreen=False);writer=None
    try:
        game.new_game();game.state='play';game.sound_on=False
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                 '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                 '-crf','18','-pix_fmt','yuv420p',str(ROOT/'output'/'lives-demo.mp4')]
        writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        font=pg.font.SysFont('Segoe UI',18);observations=[];before=game.native_canvas.uploads
        for frame in range(300):
            pg.event.pump()
            if frame in (60,120,180):game.hero.y=900
            if frame==250:game.handle_pad(PadSnapshot(start_pressed=True))
            for _ in range(2):
                game.time+=STEP
                if game.state=='play':game.update(STEP,0,False,False)
            game.draw(1)
            full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
            if frame in (30,90,150,210,270):
                observations.append({'frame':frame,'lives':game.lives,'deaths':game.deaths,'state':game.state})
                pg.image.save(full,ROOT/'output'/f'lives-{game.lives}-{game.state}.png')
            label='Trois vies : le symbole de poitrine du héros' if frame<60 else (
                'Deux vies : reprise au point de réapparition' if frame<120 else (
                'Une dernière vie' if frame<180 else (
                'Troisième mort : GAME OVER' if frame<250 else 'Start : nouvelle partie avec trois vies')))
            pg.draw.rect(screen,(17,30,36),(0,506,960,34))
            screen.blit(font.render(label,True,(255,227,153)),(18,511))
            writer.stdin.write(pg.image.tobytes(screen,'RGB'))
        writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
        if writer.returncode:raise RuntimeError(error)
        assert [item['lives'] for item in observations]==[3,2,1,0,3]
        assert observations[3]['state']=='game_over'
        (ROOT/'output'/'lives-validation.json').write_text(json.dumps({
            'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
            'new_texture_uploads':game.native_canvas.uploads-before,
            'observations':observations},indent=2),encoding='utf-8')
    finally:
        if writer is not None and writer.poll() is None:writer.kill();writer.wait()
        game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
