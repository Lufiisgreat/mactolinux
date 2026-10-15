"""Frosted-glass panels for GTK4.

GTK has no CSS backdrop-filter, so the blur is drawn in-app: a GlassBackdrop
paints soft colour blobs behind the window content, and each FrostedBox blurs
the slice of that backdrop that sits under it before its own CSS tint is drawn.
"""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Gdk, Graphene, Gsk, Gtk

BLOBS = (
    # x, y (fraction of size), radius (fraction of the larger side), rgba
    (0.15, 0.20, 0.45, (0.55, 0.45, 0.95, 0.55)),
    (0.85, 0.30, 0.40, (0.95, 0.40, 0.65, 0.45)),
    (0.55, 0.90, 0.50, (0.30, 0.70, 0.95, 0.45)),
)


def _stop(offset, colour):
    stop = Gsk.ColorStop()
    stop.offset = offset
    stop.color = colour
    return stop


# Hard-edged discs so the blur under a panel is actually visible.
DISCS = (
    (0.30, 0.38, 0.07, (0.70, 0.60, 1.00, 0.32)),
    (0.78, 0.22, 0.06, (1.00, 0.55, 0.75, 0.30)),
    (0.62, 0.72, 0.08, (0.40, 0.80, 1.00, 0.28)),
    (0.12, 0.85, 0.05, (0.95, 0.80, 0.45, 0.24)),
)


class GlassBackdrop(Gtk.Widget):
    """Decorative layer that FrostedBox panels blur."""

    def __init__(self):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_can_target(False)

    def do_snapshot(self, snapshot):
        width, height = self.get_width(), self.get_height()
        if width <= 0 or height <= 0:
            return
        scale = max(width, height)
        for x, y, radius, (red, green, blue, alpha) in BLOBS:
            centre = Graphene.Point()
            centre.init(x * width, y * height)
            rect = Graphene.Rect()
            rect.init(0, 0, width, height)
            inner = Gdk.RGBA()
            inner.red, inner.green, inner.blue, inner.alpha = red, green, blue, alpha
            outer = Gdk.RGBA()
            outer.red, outer.green, outer.blue, outer.alpha = red, green, blue, 0.0
            snapshot.append_radial_gradient(
                rect,
                centre,
                radius * scale,
                radius * scale,
                0.0,
                1.0,
                [_stop(0.0, inner), _stop(1.0, outer)],
            )
        for x, y, radius, (red, green, blue, alpha) in DISCS:
            size = radius * scale
            bounds = Graphene.Rect()
            bounds.init(x * width - size, y * height - size, 2 * size, 2 * size)
            corner = Graphene.Size()
            corner.init(size, size)
            disc = Gsk.RoundedRect()
            disc.init(bounds, corner, corner, corner, corner)
            colour = Gdk.RGBA()
            colour.red, colour.green, colour.blue, colour.alpha = red, green, blue, alpha
            snapshot.push_rounded_clip(disc)
            snapshot.append_color(colour, bounds)
            snapshot.pop()


class FrostedBox(Gtk.Box):
    """Panel that blurs the backdrop behind it; style the tint with CSS.

    The CSS class, padding and children live on an inner box so this outer
    widget has no padding and its snapshot coordinates match its allocation.
    """

    backdrop = None
    blur_radius = 28
    corner_radius = 10

    def __init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=0, radius=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.inner = Gtk.Box(orientation=orientation, spacing=spacing)
        self.inner.set_hexpand(True)
        super().append(self.inner)
        if radius is not None:
            self.corner_radius = radius

    def append(self, child):
        self.inner.append(child)

    def add_css_class(self, name):
        self.inner.add_css_class(name)

    def set_vexpand(self, expand):
        super().set_vexpand(expand)
        self.inner.set_vexpand(expand)

    def set_size_request(self, width, height):
        super().set_size_request(width, height)

    def do_snapshot(self, snapshot):
        backdrop = FrostedBox.backdrop
        width, height = self.get_width(), self.get_height()
        if backdrop is not None and backdrop.get_width() > 0 and width > 0:
            ok, origin = self.compute_point(backdrop, Graphene.Point().init(0, 0))
            if ok:
                bounds = Graphene.Rect()
                bounds.init(0, 0, width, height)
                size = Graphene.Size()
                size.init(self.corner_radius, self.corner_radius)
                rounded = Gsk.RoundedRect()
                rounded.init(bounds, size, size, size, size)
                margin = self.blur_radius * 3
                wide = Graphene.Rect()
                wide.init(-margin, -margin, width + 2 * margin, height + 2 * margin)
                snapshot.push_rounded_clip(rounded)
                snapshot.push_blur(self.blur_radius)
                snapshot.push_clip(wide)
                snapshot.translate(Graphene.Point().init(-origin.x, -origin.y))
                backdrop.do_snapshot(snapshot)
                snapshot.pop()
                snapshot.pop()
                snapshot.pop()
        Gtk.Box.do_snapshot(self, snapshot)
