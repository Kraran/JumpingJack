"""Render the level 05 art study with real hero physics and the existing GPU path.

This is a controlled visual preview, not a new campaign level. All settings and
save slots live in a temporary directory. No changes to main.py are required.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import pygame as pg

from main import Game, Platform, ROOT, STEP, GOLD
from gpu_render import SCALE
from greece_art import GreeceArt
from rendering import pixel


LENGTH = 4800
LEDGES = ((400, 490, 300), (820, 350, 240), (1200, 460, 360),
          (1710, 490, 180), (2070, 365, 300), (2500, 470, 240),
          (2910, 335, 120), (3280, 465, 360), (3780, 485, 300),
          (4200, 350, 240))
TITLE = 'MONDE 2 · LES HAUTEURS D’HÉLIOS'
SUBTITLE = '05 · LES RIVAGES D’HÉLIOS'
CAPTION = 'ÉTUDE VISUELLE · Mer Égée, marbre et bronze · Parcours de démonstration'


def configure_scene(game):
    game.state = 'play'
    game.sound_on = False
    game.world_length = LENGTH
    game.platforms = [Platform(0, 620, LENGTH+128, 140, True)]
    game.platforms += [Platform(x, y, w, 32) for x, y, w in LEDGES]
    game.gems = [(x+w*f, y-42) for x, y, w in LEDGES for f in (.28, .70)]
    game.gems += [(x, 570) for x in (220, 740, 1550, 1940, 2750, 3650, 4590)]
    game.taken.clear()
    game.beetle_spawns = ()
    game.beetle_motions = []
    game.vultures = []
    game.crocodiles = []
    game.scorpions = []
    game.gyrospheres = []
    game.vases = []
    game.obelisks = []
    game.pit_regions = []
    game.medallion_anchor = (-1000., -1000.)
    game.gamepads.rumble_enabled = False


def draw_scene(game, art, alpha=1, present=False):
    native = game.native_canvas
    native.begin()
    render_camera = game.prev_cam+(game.cam-game.prev_cam)*alpha
    camera = pixel(render_camera*SCALE)/SCALE
    art.background(native, render_camera)
    for platform in game.platforms:
        art.platform(game.canvas, platform, camera)
    clock = game.previous_elapsed+(game.elapsed-game.previous_elapsed)*alpha
    for index, (x, y) in enumerate(game.gems):
        if index not in game.taken and -40 < x-camera < 1320:
            game.crystal_sprites.draw(game.canvas, x-camera, y, clock, index)
    hero = game.hero
    game.draw_hero(hero.px+(hero.x-hero.px)*alpha-camera,
                   hero.py+(hero.y-hero.py)*alpha, alpha)
    game.solar.draw(game.canvas, hero, game.collision_platforms(), camera, alpha)
    # These panels and text textures are prepared before the measured render loop.
    game.canvas.blit_native(game.greece_header, (0, 0))
    game.canvas.blit_native(game.greece_footer, (0, 676))
    game.text(TITLE, (38, 29), 16, GOLD)
    game.text(SUBTITLE, (38, 63), 26)
    game.text('SCÈNE DE DIRECTION ARTISTIQUE', (880, 47), 13, GOLD)
    game.text(CAPTION, (640, 694), 14, center=True)
    if present:
        native.present(game.screen)


def preview(native=False, video=False):
    output = ROOT/'output'
    output.mkdir(exist_ok=True)
    writer = None
    with tempfile.TemporaryDirectory(prefix='jumpingjack-greece-') as directory:
        temporary = Path(directory)
        game = Game(not native, fullscreen=False, settings_path=temporary/'settings.json',
                    saves_path=temporary/'saves')
        try:
            art = GreeceArt(ROOT/'assets')
            configure_scene(game)
            game.greece_header = pg.Surface((1920, 158), pg.SRCALPHA).convert_alpha()
            game.greece_header.fill((14, 36, 46, 225))
            game.greece_footer = pg.Surface((1920, 66), pg.SRCALPHA).convert_alpha()
            game.greece_footer.fill((14, 36, 46, 230))
            for text, size, color in ((TITLE, 16, GOLD), (SUBTITLE, 26, (246, 236, 210)),
                                      ('SCÈNE DE DIRECTION ARTISTIQUE', 13, GOLD),
                                      (CAPTION, 14, (246, 236, 210))):
                game.cache_text(text, size, color)
            game.native_canvas.preload(art.images+[game.greece_header, game.greece_footer]
                                       +list(game.text_cache.values()))
            draw_scene(game, art)
            warm_uploads = game.native_canvas.uploads
            if video:
                import imageio_ffmpeg
                command = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error',
                           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080',
                           '-r', '60', '-i', '-', '-an', '-c:v', 'libx264',
                           '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
                           str(output/'greece-study-demo.mp4')]
                writer = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            screenshots = {60: 'coast', 310: 'athena', 670: 'acropolis'}
            observations = []
            jump_sites = iter((330, 1130, 2000, 2850, 3700))
            next_jump = next(jump_sites, float('inf'))
            frames = 720
            for frame in range(frames):
                for event in pg.event.get():
                    if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                        raise KeyboardInterrupt('Preview cancelled')
                for _ in range(2):
                    jump = game.hero.grounded and game.hero.x >= next_jump
                    if jump:
                        next_jump = next(jump_sites, float('inf'))
                    game.time += STEP
                    game.update(STEP, 1, False, jump)
                draw_scene(game, art, .5, present=native)
                if frame in screenshots:
                    name = screenshots[frame]
                    pg.image.save(game.capture(), output/f'greece-study-{name}.png')
                    observations.append({'shot': name, 'camera': round(game.cam, 2),
                                         'hero': [round(game.hero.x, 2), round(game.hero.y, 2)]})
                if writer is not None:
                    writer.stdin.write(pg.image.tobytes(game.capture(), 'RGB'))
            if writer is not None:
                writer.stdin.close()
                errors = writer.stderr.read().decode(errors='replace')
                writer.wait()
                if writer.returncode:
                    raise RuntimeError(errors)
            uploads = game.native_canvas.uploads-warm_uploads
            report = {'gpu': game.native_canvas.gpu, 'renderer': game.presentation.renderer,
                      'frames': frames, 'simulation_hz': 120, 'video_fps': 60 if video else None,
                      'new_texture_uploads_during_draw': uploads,
                      'ground_composited_with_scenery': {'middle': 0.24, 'near': 0.48},
                      'deaths': game.deaths, 'score': game.score,
                      'crystals_collected': len(game.taken), 'shots': observations,
                      'scope': 'Visual study; controlled movement with real physics and animation. '
                               'No enemies, no campaign or save-format integration. '
                               'GPU readbacks occur only for screenshots/video export.'}
            (output/'greece-study-validation.json').write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            assert game.deaths == 0, report
            assert game.score == len(game.taken)*10 and game.taken, report
            assert uploads == 0, report
            if native:
                assert game.native_canvas.gpu, 'Native check requires an accelerated renderer'
            print(json.dumps(report, ensure_ascii=False, indent=2))
        finally:
            if writer is not None and writer.poll() is None:
                writer.kill()
                writer.wait()
            game.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-check', action='store_true', help='Verify the real GPU renderer')
    parser.add_argument('--video', action='store_true', help='Also export the Full HD 60 FPS preview')
    arguments = parser.parse_args()
    preview(arguments.native_check, arguments.video)
