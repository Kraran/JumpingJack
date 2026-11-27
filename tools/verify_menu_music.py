"""Check real menu music, GPU rendering and preferences with temporary user data."""
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame as pg
from main import Game,ROOT,MENU_PAGES
from settings import Settings
from unittest.mock import patch
from loading import LoadingScreen


def verify():
    with tempfile.TemporaryDirectory(prefix='jumpingjack-music-') as directory:
        path=Path(directory)/'settings.json'
        Settings(fullscreen=False).save(path)
        loading_audio=[]
        original_show=LoadingScreen.show
        def observe(screen,*args,**kwargs):
            if args[2]>=.05:loading_audio.append(pg.mixer.music.get_busy())
            return original_show(screen,*args,**kwargs)
        with patch.object(LoadingScreen,'show',observe):
            game=Game(False,fullscreen=False,settings_path=path,saves_path=Path(directory)/'saves')
        try:
            music=game.menu_music
            assert music.available,music.error
            assert loading_audio and all(loading_audio)
            def frames(seconds):
                until=time.monotonic()+seconds
                while time.monotonic()<until:
                    for event in pg.event.get():
                        if event.type==pg.QUIT:raise KeyboardInterrupt()
                    game.draw();pg.time.wait(16)
            frames(1.)
            for page in MENU_PAGES:
                game.enter_menu(page);frames(.05)
                assert music.active and music.starts==1
            game.enter_menu('settings');game.menu.selected['settings']=6
            game.draw();pg.image.save(game.capture(),ROOT/'output/menu-music-settings.png')
            game.prepare_rendering()
            assert music.active and music.starts==1
            game.menu_action('activate');frames(2.1)
            assert not music.active and music.paused and not Settings.load(path).music
            assert game.sound_on
            game.menu_action('right');frames(.9)
            assert music.active and not music.paused and Settings.load(path).music
            game.menu.selected['settings']=1;game.menu_action('left')
            game.menu.selected['settings']=6;game.menu_action('left');frames(.9)
            assert Settings.load(path).sound_volume==90 and Settings.load(path).music_volume==90
            assert abs(game.sounds['jump'].get_volume()-.9)<.01
            assert abs(music.volume-.65*.9)<.01
            game.draw();pg.image.save(game.capture(),ROOT/'output/menu-music-settings.png')
            game.resume_from_menu();frames(1.)
            assert not music.paused and 0<music.volume<.65*.9
            frames(1.1)
            assert not music.active and music.paused
            game.enter_menu('pause');frames(.9)
            assert music.active and not music.paused and music.starts==1
            pg.mixer.music.set_pos(99.98);frames(.3)
            assert pg.mixer.music.get_busy()
            assert game.native_canvas.gpu
            report={'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                    'audio_format':pg.mixer.get_init(),'stream_starts':music.starts,
                    'playing_during_loading':all(loading_audio),'sound_volume':90,'music_volume':90,
                    'gameplay_fade_seconds':2.,'loading_fade_seconds':1.2,
                    'menu_pages':list(MENU_PAGES),'ogg_wrap':True,'gameplay_pause_and_menu_resume':True,
                    'independent_setting_persisted':True,'render_warmup_preserves_music':True,
                    'error':music.error,'user_settings_and_saves':'temporary files only'}
            (ROOT/'output/menu-music-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report,indent=2))
        finally:game.close()


if __name__=='__main__':verify()
