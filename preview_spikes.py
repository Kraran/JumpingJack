"""Real spike gameplay: upward death, safe drop-through and safe side contact."""
import argparse
import json
import subprocess
import pygame as pg
from main import Game,Hero,STEP,ROOT


def preview(native=False):
    import imageio_ffmpeg
    game=Game(not native,fullscreen=False);output=ROOT/'output';writer=None;checks=[];vibrations=[]
    original_rumble=game.gamepads.rumble
    def rumble(event):
        vibrations.append(event)
        return original_rumble(event)
    game.gamepads.rumble=rumble
    try:
        game.sound_on=False
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                 '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                 '-crf','18','-pix_fmt','yuv420p',str(output/'platform-spikes-demo.mp4')]
        writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        font=pg.font.SysFont('Segoe UI',19)
        for stage in range(3):
            game.reset();game.state='play';game.checkpoint=(4740,620);game.check_index=1
            game.obelisk.active=True;game.obelisk.clock=game.obelisk.previous_clock=2
            game.hero=Hero(5190 if stage==2 else 5328,535 if stage==2 else 470 if stage==1 else 620)
            game.hero.grounded=stage!=2
            if stage==2:game.hero.vx=340;game.hero.vy=105
            for frame in range(140):
                pg.event.pump();game.invuln=100
                for step in range(2):
                    game.time+=STEP
                    press=stage!=2 and frame==20 and step==0
                    game.update(STEP,1 if stage==2 else 0,stage!=0,press,
                                drop=stage==1 and press,down=stage==1)
                game.cam=game.prev_cam=4580;game.draw(.5)
                full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
                detail=pg.transform.scale(full.subsurface((930,680,540,180)),(540,180))
                screen.blit(detail,(385,110));pg.draw.rect(screen,(223,186,102),(384,109,542,182),1)
                pg.draw.rect(screen,(17,30,36),(0,506,960,34))
                labels=('Saut sous les pointes : mort','Bas + A : descente sans danger','Contact latéral en planant : chute, sans mort')
                screen.blit(font.render(labels[stage],True,(255,227,153)),(18,511))
                if stage==0 and frame==10:
                    pg.image.save(full,output/'platform-spikes-game.png')
                    pg.image.save(screen,output/'platform-spikes-preview.png')
                writer.stdin.write(pg.image.tobytes(screen,'RGB'))
            checks.append(game.deaths)
        writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
        if writer.returncode:raise RuntimeError(error)
        assert checks==[1,0,0],checks
        assert vibrations.count('death')==1,vibrations
        (output/'platform-spikes-validation.json').write_text(json.dumps({
            'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
            'deaths_upward_drop_side':checks,'spiked_platforms':[p.x for p in game.platforms if p.spiked],
            'death_vibration_events':vibrations.count('death'),
            'shared_spike_atlas_cached':id(game.spike_sprites.atlas) in game.native_canvas.textures if game.native_canvas.gpu else None,
            'frames':420},indent=2),encoding='utf-8')
    finally:
        if writer is not None and writer.poll() is None:writer.kill();writer.wait()
        game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
