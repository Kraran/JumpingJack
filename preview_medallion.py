"""High medallion pickup with the same synthesized four-note reward melody."""
import argparse
import json
import subprocess
import wave
from array import array
import pygame as pg
from main import Game,Hero,STEP,ROOT
from medallion import POSITION,MedallionInventory,tune


def preview(native=False):
    import imageio_ffmpeg
    game=Game(not native,fullscreen=False);output=ROOT/'output';writer=None
    silent=output/'ra-medallion-silent.mp4';audio=output/'ra-medallion-demo-audio.wav'
    try:
        game.state='play';game.sound_on=False;game.invuln=100
        game.medallions=MedallionInventory()
        game.hero=Hero(POSITION[0],455);game.hero.grounded=True
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo',
                 '-pix_fmt','rgb24','-s','960x540','-r','60','-i','-','-an','-c:v','libx264',
                 '-crf','18','-pix_fmt','yuv420p',str(silent)]
        writer=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        font=pg.font.SysFont('Segoe UI',18);picked=None;seen=set();before=game.native_canvas.uploads
        frames=240
        for frame in range(frames):
            pg.event.pump()
            for step in range(2):
                game.time+=STEP
                game.update(STEP,0,False,frame==60 and step==0)
            if picked is None and game.medallions.count:picked=frame
            game.cam=game.prev_cam=6020
            protection=game.invuln;game.invuln=0
            try:game.draw(.5)
            finally:game.invuln=protection
            full=game.capture();screen=pg.transform.smoothscale(full,(960,540))
            index=int((game.elapsed/2.4%1)*48);seen.add(index)
            detail=pg.transform.scale(game.medallion_sprites.atlas.subsurface(game.medallion_sprites.world[index]),(256,256))
            pg.draw.rect(screen,(25,39,47),(660,90,270,270));screen.blit(detail,(667,97))
            pg.draw.rect(screen,(17,30,36),(0,506,960,34))
            label='Fragment de Rê : un médaillon rare, au sommet du saut' if picked is None else 'Médaillon obtenu : compteur conservé, mélodie de récompense'
            screen.blit(font.render(label,True,(255,227,153)),(18,511))
            if frame==45:
                pg.image.save(full,output/'ra-medallion-game.png')
                pg.image.save(screen,output/'ra-medallion-preview.png')
            writer.stdin.write(pg.image.tobytes(screen,'RGB'))
        writer.stdin.close();error=writer.stderr.read().decode(errors='replace');writer.wait()
        if writer.returncode:raise RuntimeError(error)
        assert picked is not None and game.medallions.count==1
        rate=48000;channels=2;chime=tune(rate,channels)
        with wave.open(str(output/'ra-medallion-jingle.wav'),'wb') as wav:
            wav.setnchannels(channels);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(chime.tobytes())
        samples=array('h',[0])*(round(frames/60*rate)*channels)
        offset=round(picked/60*rate)*channels;samples[offset:offset+len(chime)]=chime
        with wave.open(str(audio),'wb') as wav:
            wav.setnchannels(channels);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(samples.tobytes())
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-i',str(silent),'-i',str(audio),
                        '-c:v','copy','-c:a','aac','-shortest',str(output/'ra-medallion-demo.mp4')],check=True,
                       creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (output/'ra-medallion-validation.json').write_text(json.dumps({
            'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,'position':POSITION,
            'pickup_frame':picked,'pickup_seconds_after_jump':(picked-60)/60,
            'inventory_count':game.medallions.count,'frames_observed':len(seen),
            'new_texture_uploads':game.native_canvas.uploads-before,'music_notes':4,
            'audio_note':'Video uses the same PCM tune as the game, synchronized to pickup.'},indent=2),encoding='utf-8')
        game.medallions.collect(2);game.medallions.collect(3)
        if game.medallions.redeem_extra_life():game.lives+=1;game.extra_life_notice=3.
        game.draw(1)
        pg.image.save(game.capture(),output/'ra-medallion-extra-life.png')
    finally:
        if writer is not None and writer.poll() is None:writer.kill();writer.wait()
        game.close()
        for temporary in (silent,audio):
            if temporary.exists():temporary.unlink()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-check',action='store_true')
    preview(parser.parse_args().native_check)
