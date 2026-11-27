"""Verify real GPU output, cropped margins, mouse mapping and persisted bezel menu."""
import ctypes
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame as pg
from main import Game,ROOT
from settings import Settings
from rendering import integer_viewport
from bezel import margins


def logical_point(game,x,y):
    sdl=ctypes.CDLL(str(Path(pg.__file__).parent/'SDL2.dll'))
    get_window=sdl.SDL_GetWindowFromID;get_window.argtypes=[ctypes.c_uint32];get_window.restype=ctypes.c_void_p
    get_renderer=sdl.SDL_GetRenderer;get_renderer.argtypes=[ctypes.c_void_p];get_renderer.restype=ctypes.c_void_p
    convert=sdl.SDL_RenderWindowToLogical
    convert.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float)]
    convert.restype=None
    result_x=ctypes.c_float();result_y=ctypes.c_float()
    convert(get_renderer(get_window(game.sdl_window.id)),x,y,ctypes.byref(result_x),ctypes.byref(result_y))
    return result_x.value,result_y.value


def verify():
    observations=[]
    with tempfile.TemporaryDirectory(prefix='jumpingjack-bezels-') as directory:
        temp=Path(directory);path=temp/'settings.json'
        Settings(fullscreen=False,music=False).save(path)
        game=Game(False,fullscreen=False,settings_path=path,saves_path=temp/'saves')
        try:
            assert game.native_canvas.gpu
            game.sdl_window.hide()
            game.new_game();game.start_level(5);game.state='play'
            for resolution in ((2560,1080),(3840,1080),(3440,1440),(1920,1200),(3840,2160)):
                game.sdl_window.size=resolution;pg.event.pump()
                game.set_bezel('none');game.draw(present=False)
                baseline=pg.image.tobytes(game.capture(),'RGB')
                for mode in ('egypt','greece','solar','none'):
                    game.set_bezel(mode);game.draw(present=False)
                    source=game.capture()
                    assert pg.image.tobytes(source,'RGB')==baseline,(resolution,mode,'scene changed with bezel')
                    before=game.native_canvas.uploads
                    image=game.native_canvas.present(game.screen,capture=True)
                    output=image.get_size();size,pos=integer_viewport(output,(1920,1080));viewport=pg.Rect(pos,size)
                    expected=source if size==source.get_size() else pg.transform.scale(source,size)
                    assert pg.image.tobytes(image.subsurface(viewport),'RGB')==pg.image.tobytes(expected,'RGB'),(resolution,mode,'game pixels changed')
                    assert game.native_canvas.renderer.logical_size==(1920,1080)
                    assert game.native_canvas.uploads==before,(resolution,mode,'late texture upload')
                    for _,rect in margins(output,viewport):
                        pixel=image.get_at(rect.center)[:3]
                        assert (pixel==(10,17,22))==(mode=='none'),(resolution,mode,pixel)
                    # Query SDL's actual native mouse conversion after presentation.
                    factor=size[0]/1920
                    point=logical_point(game,pos[0]+round(600*factor),pos[1]+round(450*factor))
                    assert abs(point[0]-600)<.01 and abs(point[1]-450)<.01,(resolution,point)
                    if resolution in ((2560,1080),(3840,1080)) and mode!='none':
                        pg.image.save(image,ROOT/'output'/f'bezel-{mode}-{resolution[0]}.png')
                    observations.append({'output':output,'mode':mode,'game_viewport':list(viewport),
                                         'game_pixels_identical':True,'late_texture_uploads':0,'mouse_mapping_correct':True})
            for level in range(1,9):
                game.start_level(level);game.state='play';game.set_bezel('auto');game.draw(present=False)
                assert game.native_canvas.bezel_theme==('egypt' if level<5 else 'greece')
            game.sdl_window.size=(2560,1080);pg.event.pump()
            game.enter_menu('settings');game.menu.selected['settings']=7;game.menu_action('activate')
            assert game.state=='bezels'
            game.menu.selected['bezels']=1;game.menu_action('activate');game.draw(present=False)
            image=game.native_canvas.present(game.screen,capture=True)
            pg.image.save(image,ROOT/'output/bezel-selection-menu.png')
            assert Settings.load(path).bezel=='auto'
            report={'renderer':game.presentation.renderer,'gpu':True,'cases':observations,
                    'auto_worlds_1_to_8':True,'selection_saved':True,'user_data':'temporary preferences and saves only'}
            (ROOT/'output/bezel-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report,indent=2))
        finally:game.close()


if __name__=='__main__':verify()
