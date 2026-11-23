"""Capture the actual crocodile encounter: lethal approach, then a safe jump."""
import argparse
import subprocess
import pygame as pg
from main import Game, Hero, ROOT, STEP


def export():
    import imageio_ffmpeg
    game=Game(True);game.sound_on=False
    output=ROOT/'output';output.mkdir(exist_ok=True)
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
             '-s','960x540','-r','60','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','18',
             '-pix_fmt','yuv420p',str(output/'crocodile-demo.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    captured=set()
    deaths=[]
    try:
        for frame in range(420):
            if frame in (0,150):
                game.reset();game.state='play'
                game.hero=Hero(580,620);game.hero.grounded=True
                game.cam=game.prev_cam=180
            local=frame if frame<150 else frame-150
            for substep in range(2):
                game.time+=STEP
                axis=1 if not game.deaths and game.hero.x<1480 else 0
                jump=frame>=150 and local==20 and substep==0
                held=frame>=150 and game.hero.x<1450
                game.update(STEP,axis,held,jump)
            game.draw(1)
            caption=('Approche au sol : charge mortelle' if not game.deaths else 'Contact mortel : retour au point de reprise') if frame<150 else 'Saut et vol plane : rester hors de portee'
            game.text(caption,(640,102),22,(237,194,105),center=True)
            state=game.crocodiles[0].state
            if state not in captured:
                pg.image.save(game.capture(),str(output/f'crocodile-{state}-game.png'));captured.add(state)
            image=pg.transform.smoothscale(game.capture(),(960,540))
            process.stdin.write(pg.image.tostring(image,'RGB'))
            if frame in (149,419):deaths.append(game.deaths)
        process.stdin.close();process.stdin=None
        _,errors=process.communicate()
        if process.returncode:raise RuntimeError(errors.decode('utf-8','replace'))
        assert deaths==[1,0],f'Encounter verification failed: {deaths}'
    finally:
        if process.poll() is None:process.kill();process.wait()
        game.close()
    print('Approche au sol: 1 mort; saut et vol plane: aucune mort.')
    print(output/'crocodile-demo.mp4')


def verify_native():
    import json
    import statistics
    import time
    from dataclasses import asdict
    game=Game();game.state='play';game.sound_on=False
    game.hero=Hero(580,620);game.hero.grounded=True;game.cam=game.prev_cam=180
    previous=time.perf_counter();acc=0.;simulation=0.;phase=0;jumped=False;times=[];deaths=[]
    try:
        for _ in range(420):
            game.pacer.wait(game.presentation.vsync,game.presentation.refresh_hz)
            if any(e.type==pg.QUIT or (e.type==pg.KEYDOWN and e.key==pg.K_ESCAPE) for e in pg.event.get()):raise KeyboardInterrupt
            now=time.perf_counter();dt=min(now-previous,.1);previous=now;acc+=dt;game.time+=dt
            while acc>=STEP:
                if phase==0 and simulation>=2.5:
                    deaths.append(game.deaths);game.reset();game.state='play'
                    game.hero=Hero(580,620);game.hero.grounded=True;game.cam=game.prev_cam=180;phase=1
                jump=phase==1 and simulation-2.5>=1/3 and not jumped
                if jump:jumped=True
                game.update(STEP,1 if not game.deaths and game.hero.x<1480 else 0,
                            phase==1 and game.hero.x<1450,jump)
                simulation+=STEP;acc-=STEP
            game.draw(max(0,min(1,acc/STEP)));times.append(time.perf_counter())
        intervals=[b-a for a,b in zip(times[60:],times[61:])]
        report={'display':asdict(game.presentation),'render_size':[1920,1080],
            'gpu':game.native_canvas.gpu,'samples':len(intervals),
            'fps':round(len(intervals)/sum(intervals),2),
            'p95_ms':round(sorted(intervals)[int(len(intervals)*.95)]*1000,2),
            'late_frames':sum(t>1.5/game.presentation.refresh_hz for t in intervals),
            'cpu_median_ms':round(statistics.median(game.submission_times)*1000,3),
            'crocodile_poses':len(game.crocodile_sprites.walk)+len(game.crocodile_sprites.attack)+len(game.crocodile_sprites.turn),
            'crocodile_textures_cached':all(id(im) in game.native_canvas.textures for im in game.crocodile_sprites.images),
            'first_attempt_deaths':deaths,'jump_attempt_deaths':game.deaths}
        assert deaths==[1] and game.deaths==0
        assert report['crocodile_textures_cached'] and report['gpu']
        (ROOT/'output'/'crocodile-gpu-timing.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(report,flush=True)
    finally:game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-check',action='store_true')
    args=parser.parse_args()
    verify_native() if args.native_check else export()
