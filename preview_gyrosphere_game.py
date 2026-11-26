"""Native GPU check: actual pursuit, screen loss, contact death and solar kill."""
import json
import math
from pathlib import Path
import tempfile
import pygame as pg
from main import Game,Hero,ROOT,STEP
from terrain import sand_height
from gyrosphere import POINTS
import tower_level as tower


def check():
    with tempfile.TemporaryDirectory() as folder:
        g=Game(False,fullscreen=False,settings_path=Path(folder)/'settings.json',saves_path=Path(folder)/'saves')
        uploads=0
        try:
            g.sound_on=False;g.gamepads.rumble_enabled=False
            def stage(row=14):
                g.new_game();g.start_level(4);g.state='play';g.invuln=100
                x,y,w=tower.LEDGES[row];g.hero=Hero(x+w/2,y);g.hero.grounded=True
                g.cam_y=g.prev_cam_y=tower.camera_target(y)
            def frame(fire=False):
                nonlocal uploads
                pg.event.pump()
                for i in range(2):g.update(STEP,0,False,False,fire=fire and i==0);g.time+=STEP
                before=g.native_canvas.uploads;g.draw(1,present=False)
                uploads+=g.native_canvas.uploads-before
            stage();orb=g.gyrospheres[0];start=orb.x
            for _ in range(180):frame()
            assert orb.state=='chase' and orb.x<start-60
            pg.image.save(g.capture(),ROOT/'output'/'gyrosphere-expanded-tower.png')
            x,y,w=tower.LEDGES[25];g.hero=Hero(x+w/2,y);g.hero.grounded=True
            g.cam_y=g.prev_cam_y=tower.camera_target(y)
            for _ in range(150):frame()
            assert orb.state=='idle' and not orb.route and abs(orb.vx)+abs(orb.vy)<.02
            stage();orb=g.gyrospheres[0];g.invuln=0
            orb.x=orb.px=g.hero.x+20;orb.y=orb.py=g.hero.y-27
            for _ in range(15):frame()
            assert g.hero_death.kind=='gyrosphere' and g.hero_death.electrical
            pg.image.save(g.capture(),ROOT/'output'/'gyrosphere-expanded-electric-death.png')
            for _ in range(160):frame()
            assert g.lives==2 and not g.hero_death.active and not g.resurrection.active
            stage();orb=g.gyrospheres[0];orb.x=orb.px=g.hero.x+120;orb.y=orb.py=g.hero.y-54
            for i in range(20):frame(fire=i==0)
            assert not orb.alive
            pg.image.save(g.capture(),ROOT/'output'/'gyrosphere-expanded-solar-destruction.png')
            counts={4:len(g.gyrospheres)}
            for level in (2,3):
                g.new_game();g.start_level(level);g.state='play';g.invuln=100
                counts[level]=len(g.gyrospheres)
                for index,enemy in enumerate(g.gyrospheres):
                    x=10590. if level==2 else enemy.home[0]-120
                    y=sand_height(x) if level==2 else 620.
                    g.hero=Hero(x,y);g.hero.grounded=True;g.cam=g.prev_cam=x-512
                    distance=math.dist((enemy.x,enemy.y),(g.hero.x,g.hero.y-27))
                    for _ in range(240 if level==2 else 120):frame()
                    assert enemy.state=='chase'
                    assert math.dist((enemy.x,enemy.y),(g.hero.x,g.hero.y-27))<distance
                    # Render the protected hero steadily for the still image.
                    g.invuln=0;g.draw(1,present=False);g.invuln=100
                    pg.image.save(g.capture(),ROOT/'output'/f'gyrosphere-level{level}-{index+1}.png')
            assert counts=={2:1,3:2,4:6}
            report=dict(gpu=g.native_canvas.gpu,new_texture_uploads=uploads,counts=counts,points=POINTS,
                        pursuit=True,screen_loss=True,electric_death=True,solar_destruction=True)
            assert uploads==0,report
            (ROOT/'output'/'gyrosphere-game-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(report)
        finally:g.close()


if __name__=='__main__':check()
