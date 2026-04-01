from .yantra    import Yantra
from .cube      import Cube
from .plasma    import Plasma
from .tunnel    import Tunnel
from .lissajous import Lissajous
from .corridor  import Corridor
from .nova      import Nova
from .spiral    import Spiral
from .bubbles   import Bubbles
from .triflux  import Attractor
from .branches  import Branches
from .spectrum  import Bars
from .waterfall import GlowSquares

MODES = [
    ("Yantra",      Yantra),      # 1
    ("Cube",        Cube),        # 2
    ("Plasma",      Plasma),      # 3
    ("Lissajous",   Lissajous),   # 4
    ("Tunnel",      Tunnel),      # 5
    ("Corridor",    Corridor),    # 6
    ("Nova",        Nova),        # 7
    ("Spiral",      Spiral),      # 8
    ("Bubbles",     Bubbles),     # 9
    ("TriWall",     Attractor),   # ←/→ only
    ("Branches",    Branches),    # ←/→ only
    ("Spectrum",    Bars),        # ←/→ only
    ("Waterfall",   GlowSquares), # ←/→ only
]
