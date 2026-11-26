"""Advance noninteractive life transitions before asserting resumed gameplay."""
def finish_respawn(game):
    from main import STEP
    for _ in range(500):
        if not (game.hero_death.active or game.resurrection.active):return
        game.update(STEP,0,False,False)
    raise AssertionError('Life transition did not finish')
