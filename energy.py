"""Solar gameplay budget with an independently smoothed fixed-step HUD."""
import math

MAX_ENERGY=100.
GLIDE_PER_SECOND=4.
RAY_COST=30.
SHARD_ENERGY=10.


class SolarEnergy:
    def __init__(self):self.reset()

    def reset(self):
        self.value=MAX_ENERGY
        self.display=self.previous_display=MAX_ENERGY
        self.fast_timer=0.
        self.warning=0.

    @property
    def can_glide(self):return self.value>1e-9

    def drain_glide(self,dt):
        self.value=max(0.,self.value-GLIDE_PER_SECOND*dt)
        if self.value<1e-9:self.value=0.

    def spend_ray(self):
        if self.value+1e-9<RAY_COST:
            self.warning=.7
            return False
        self.value=max(0.,self.value-RAY_COST)
        self.fast_timer=.2
        return True

    def collect(self):
        self.value=min(MAX_ENERGY,self.value+SHARD_ENERGY)
        if self.value>=RAY_COST:self.warning=0.

    def refill(self):
        self.value=MAX_ENERGY
        self.warning=0.;self.fast_timer=0.

    def update_display(self,dt):
        self.previous_display=self.display
        rate=35. if self.fast_timer>0 else 14.
        self.display+=(self.value-self.display)*(1-math.exp(-rate*dt))
        if abs(self.display-self.value)<.005:self.display=self.value
        self.fast_timer=max(0.,self.fast_timer-dt)
        if self.fast_timer<1e-9:self.fast_timer=0.
        self.warning=max(0.,self.warning-dt)

    def fraction(self,alpha=1.):
        alpha=max(0.,min(1.,alpha))
        return max(0.,min(1.,(self.previous_display+(self.display-self.previous_display)*alpha)/MAX_ENERGY))
