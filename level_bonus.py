"""Presentation-only life bonus counter; awarded points and lives never change."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BonusFrame:
    remaining:int
    counted:int
    progress:float
    flying:bool
    points:int


def sample(elapsed,lives):
    lives=max(0,lives)
    step=min(.55,3/max(1,lives))
    t=max(0.,elapsed-.5)
    counted=min(lives,int(t/step+1e-9))
    progress=max(0.,min(1.,(t-counted*step)/step)) if counted<lives else 0.
    flying=elapsed>=.5 and counted<lives
    p=max(0.,min(1.,(progress-.7)/.3)) if flying else 0.
    points=counted*100+round(100*p*p*(3-2*p))
    return BonusFrame(lives-counted,counted,progress,flying,points)
