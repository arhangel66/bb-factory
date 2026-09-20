"""The one error that means "the other side", so the board can tell weather from a fault of its own."""


class Remote(RuntimeError):
    """bb or Telegram did not answer, or answered badly: the next try may go through.

    A RuntimeError the factory raises anywhere else is a fault of its own code, and retrying it for five
    minutes only repeats it."""
