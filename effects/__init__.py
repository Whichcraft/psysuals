from .yantra   import Yantra
from .cube     import Cube
from .plasma   import Plasma
from .tunnel   import Tunnel
from .lissajous import Lissajous
from .corridor import Corridor
from .nova     import Nova
from .spiral   import Spiral
from .bubbles  import Bubbles
from .spectrum import Bars
from .waterfall import GlowSquares

MODES = [
    ("Yantra",      Yantra),      # 1
    ("Cube",        Cube),        # 2
    ("Plasma",      Plasma),      # 3
    ("Tunnel",      Tunnel),      # 4
    ("Lissajous",   Lissajous),   # 5
    ("Corridor",    Corridor),    # 6
    ("Nova",        Nova),        # 7
    ("Spiral",      Spiral),      # 8
    ("Bubbles",     Bubbles),     # 9
    ("Spectrum",    Bars),        # 0
    ("Waterfall",   GlowSquares), # arrow-key navigation only
]
