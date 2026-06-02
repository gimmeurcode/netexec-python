"""
base.py — NETEXEC
==================
Abstract base class that establishes the contract for every screen renderer.

A Screen receives the live GameUI controller (``ctx``) and the current
GameState.  It writes to ``ctx.screen``, appends to ``ctx._click_regions``
and ``ctx._tooltip_regions``, and navigates by assigning to ``ctx.screen``.

No screen module may import another screen module directly; all cross-screen
orchestration goes through the GameUI controller.
"""


class Screen:
    """
    Base class for per-screen renderers.

    Invariant
    ---------
    render()        is called once per frame for the active screen.
    handle_event()  is called for every pygame KEYDOWN event while active.
                    The default implementation is a no-op; override only
                    when the screen needs keyboard-driven state changes
                    beyond what the global handler in GameUI covers.
    """

    def render(self, ctx, state):
        """
        Draw the screen to ctx.screen for this frame.

        Parameters
        ----------
        ctx   : GameUI  Live controller (surface, fonts, mouse pos, …).
        state : GameState
        """
        raise NotImplementedError

    def handle_event(self, event, state, ctx):
        """
        Handle a KEYDOWN pygame event for this screen.

        Parameters
        ----------
        event : pygame.event.Event  KEYDOWN event.
        state : GameState
        ctx   : GameUI
        """
