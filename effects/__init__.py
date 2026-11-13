from .yantra      import Yantra
from .cube        import Cube
from .plasma_gl   import PlasmaGL as Plasma
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
from .fireworks        import Fireworks
from .aurora             import Aurora
from .lattice            import Lattice
from .mycelium    import Mycelium
from .magnetar    import Magnetar
from .slimemold   import SlimeMold
from .mobius      import Mobius
from .chromatic   import Chromatic
from .persistence import Persistence
from .synapse     import Synapse
from .heartbeat   import Heartbeat
from .hyperbolic import Hyperbolic
from .liquidlight import LiquidLight
from .cymatica import Cymatica
from .phason import Phason
from .tesseract import Tesseract
from .ferrofluid import Ferrofluid
from .chromaweave import ChromaWeave
from .horizon import Horizon
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
    ("Butterflies", Butterflies), # ←/→ only
    ("FlowField",   FlowField),   # ←/→ only
    ("Fireworks",   Fireworks),   # ←/→ only
    ("Aurora",      Aurora),      # ←/→ only
    ("Lattice",     Lattice),     # ←/→ only
    ("Mycelium",    Mycelium),    # ←/→ only
    ("Magnetar",    Magnetar),    # ←/→ only
    ("SlimeMold",   SlimeMold),   # ←/→ only
    ("Mobius",      Mobius),      # ←/→ only
    ("Chromatic",   Chromatic),   # ←/→ only
    ("Persistence", Persistence), # ←/→ only
    ("Synapse",     Synapse),     # ←/→ only
    ("Heartbeat",   Heartbeat),   # ←/→ only
    ("Hyperbolic",   Hyperbolic),     # ←/→ only
    ("LiquidLight",  LiquidLight),    # ←/→ only
    ("Cymatica",     Cymatica),       # ←/→ only
    ("Phason",       Phason),         # ←/→ only
    ("Tesseract",    Tesseract),      # ←/→ only
    ("Ferrofluid",   Ferrofluid),     # ←/→ only
    ("ChromaWeave",  ChromaWeave),    # ←/→ only
    ("Horizon",      Horizon),        # ←/→ only
    # ── Spectrum and Waterfall must always be the final two entries ──
    ("Spectrum",    Bars),        # ←/→ only — always second-to-last
    ("Waterfall",   GlowSquares), # ←/→ only — always last
]


MODE_NAMES = [name for name, _ in MODES]
# Horizon was inserted here; files saved before modes were stored by name
# hold indices that pointed one slot earlier from this position on.
_NAMELESS_SHIFT_FROM = MODE_NAMES.index("Horizon")


def resolve_mode(index, name=None):
    """Registry index for a saved mode, preferring its saved name.

    Settings and presets now store the mode name next to its index, so a
    registry insertion no longer moves the user to a different effect. Data
    saved without a name predates Horizon and is shifted past its slot.
    """
    if isinstance(name, str):
        if name in MODE_NAMES:
            return MODE_NAMES.index(name)
        return index
    return index + 1 if index >= _NAMELESS_SHIFT_FROM else index
