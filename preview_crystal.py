"""Native game preview of solar-crystal pulse, embers, collection and recharge."""
import argparse
import json
import subprocess
import pygame as pg
from main import Game,Hero,STEP,ROOT


def preview(native=False):
    import imageio_ffmpeg
    game=Game(not native,fullscreen=False);output=ROOT/'output';writer=None
    try:
        game.reset();game.state='play';game.sound_on=False;game.invuln=100
        game.hero=Hero(100,620);game.hero.grounded=True
        game.energy.value=game.energy.display=game.energy.previous_display=35
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                 '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                 '-crf','18','-pix_fmt','yuv420p',str(output/'solar-crystal-demo.mp4')]
        writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        font=pg.font.SysFont('Segoe UI',19);seen=set();before=game.native_canvas.uploads
        for frame in range(240):
            pg.event.pump()
            for _ in range(2):
                game.time+=STEP
                game.update(STEP,1 if frame>=120 else 0,False,False)
            game.cam=game.prev_cam=0;game.draw(.5)
            full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
            t=game.previous_elapsed+(game.elapsed-game.previous_elapsed)*.5
            index=game.crystal_sprites.sample(t);seen.add(index)
            area=game.crystal_sprites.areas[index]
            detail=pg.transform.scale(game.crystal_sprites.atlas.subsurface(area),(288,288))
            pg.draw.rect(screen,(25,39,47),(630,90,300,300));screen.blit(detail,(636,96))
            pg.draw.rect(screen,(17,30,36),(0,506,960,34))
            label='Cristal solaire : pulsation, braises et flottement' if frame<120 else 'Ramassage : +10 énergie par cristal'
            screen.blit(font.render(label,True,(255,227,153)),(18,511))
            if frame==70:
                pg.image.save(full,output/'solar-crystal-game.png')
                pg.image.save(screen,output/'solar-crystal-preview.png')
            writer.stdin.write(pg.image.tobytes(screen,'RGB'))
        writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
        if writer.returncode:raise RuntimeError(error)
        assert len(game.taken)==2 and game.energy.value==55
        assert len(seen)==48
        (output/'solar-crystal-validation.json').write_text(json.dumps({
            'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
            'animation_frames_observed':len(seen),'collected':len(game.taken),
            'energy_before':35,'energy_after':game.energy.value,
            'atlas_cached':id(game.crystal_sprites.atlas) in game.native_canvas.textures if game.native_canvas.gpu else None,
            'new_texture_uploads_in_game':game.native_canvas.uploads-before},indent=2),encoding='utf-8')
    finally:
        if writer is not None and writer.poll() is None:writer.kill();writer.wait()
        game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
