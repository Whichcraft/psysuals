from .yantra      import Yantra
from .cube        import Cube
from .plasma      import Plasma
from .tunnel      import Tunnel
from .lissajous   import Lissajous
from .corridor    import Corridor
from .nova        import Nova
from .spiral      import Spiral
from .bubbles     import Bubbles
from .triflux     import Attractor
from .branches    import Branches
from .butterflies        import Butterflies
from .flowfield          import FlowField
from .vortex             import Vortex
from .aurora             import Aurora
from .lattice            import Lattice
from .spectrum           import Bars
from .waterfall   import GlowSquares

MODES = [
    ("Yantra",      Yantra),      # 1
    ("Cube",        Cube),        # 2
    ("TriFlux",     Attractor),   # 3
    ("Lissajous",   Lissajous),   # 4
    ("Tunnel",      Tunnel),      # 5
    ("Corridor",    Corridor),    # 6
    ("Nova",        Nova),        # 7
    ("Spiral",      Spiral),      # 8
    ("Bubbles",     Bubbles),     # 9
    ("Plasma",      Plasma),      # ←/→ only
    ("Branches",    Branches),    # ←/→ only
    ("Butterflies", Butterflies),      # ←/→ only
    ("FlowField",   FlowField),         # ←/→ only
    ("Vortex",      Vortex),   # ←/→ only
    ("Aurora",      Aurora),   # ←/→ only
    ("Lattice",     Lattice),  # ←/→ only
    # ── Spectrum and Waterfall must always be the final two entries ──
    ("Spectrum",    Bars),        # ←/→ only — always second-to-last
    ("Waterfall",   GlowSquares), # ←/→ only — always last
]
