"""Reversible idle seating on the fixed simulation timeline."""
IDLE_DELAY=6.
REST_TIME=.8


class RestPose:
    def __init__(self):self.reset()

    def reset(self):
        self.idle=0.
        self.progress=self.previous_progress=0.
        self.state='awake'
        self.facing=1

    @property
    def active(self):return self.state!='awake'

    def update(self,dt,activity,eligible,facing=1):
        if not eligible:
            self.reset();return
        self.previous_progress=self.progress
        if activity:
            self.idle=0.
            if self.active:self.state='rising'
        if self.state=='awake':
            self.idle=0. if activity else self.idle+dt
            if self.idle+1e-9>=IDLE_DELAY:
                self.state='sitting';self.facing=facing;self.idle=0.
        if self.state=='sitting':
            self.progress=min(1.,self.progress+dt/REST_TIME)
            if self.progress>=1-1e-9:self.progress=1.;self.state='seated'
        elif self.state=='rising':
            self.progress=max(0.,self.progress-dt/REST_TIME)
            if self.progress<1e-9:self.progress=0.;self.state='awake'

    def sample(self,clip,alpha=1):
        progress=self.previous_progress+(self.progress-self.previous_progress)*max(0.,min(1.,alpha))
        return clip[min(len(clip)-1,round(progress*(len(clip)-1)))]
