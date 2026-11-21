"""Bank name labels that do not overlap each other or the bank pins.

Each label tries a ring of positions around its pin (right, left, above, below, then further out).
The first position whose text box is clear of every pin and every label already placed is used.
Labels moved well away from their pin get a thin leader line back to it.
"""
import matplotlib.patheffects as pe

# (dx, dy) in points, with the text alignment that keeps the label beside the pin.
_RING = [(9, -7, 'left', 'center'), (9, 6, 'left', 'center'), (-9, -7, 'right', 'center'),
         (-9, 6, 'right', 'center'), (0, 14, 'center', 'bottom'), (0, -16, 'center', 'top'),
         (9, -18, 'left', 'center'), (-9, -18, 'right', 'center'), (9, 17, 'left', 'center'),
         (-9, 17, 'right', 'center')]


def _overlaps(a, b):
    return not (a.x1 < b.x0 or b.x1 < a.x0 or a.y1 < b.y0 or b.y1 < a.y0)


def place_bank_labels(ax, banks, fontsize=7.2, color='white', stroke='#061b33', zorder=8,
                      pin_half=(7, 11), bold=True):
    """banks: iterable of dicts with name, lat, lon (already filtered to the map extent)."""
    from matplotlib.transforms import Bbox
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    axbox = ax.get_window_extent(renderer)
    pts = [(b, ax.transData.transform((float(b['lon']), float(b['lat'])))) for b in banks]
    px = fig.dpi / 72.0
    hw, hh = pin_half[0] * px, pin_half[1] * px
    taken = [Bbox.from_extents(x - hw, y - hh, x + hw, y + hh) for _, (x, y) in pts]

    # Crowded pins first, so they get the best spots.
    def crowd(item):
        _, (x, y) = item
        return -sum(1 for _, (x2, y2) in pts if abs(x2 - x) < 120 * px and abs(y2 - y) < 40 * px)
    order = sorted(pts, key=crowd)

    style = dict(textcoords='offset points', fontsize=fontsize, color=color, zorder=zorder,
                 fontweight='bold' if bold else 'normal')
    for bank, _ in order:
        xy = (float(bank['lon']), float(bank['lat']))
        chosen = None
        for scale in (1, 1.8, 2.6):
            for dx, dy, ha, va in _RING:
                off = (dx * scale, dy * scale)
                t = ax.annotate(bank['name'], xy, xytext=off, ha=ha, va=va, **style)
                box = t.get_window_extent(renderer).expanded(1.06, 1.15)
                inside = axbox.x0 <= box.x0 and box.x1 <= axbox.x1 and axbox.y0 <= box.y0 and box.y1 <= axbox.y1
                if inside and not any(_overlaps(box, o) for o in taken):
                    chosen = (t, box, off)
                    break
                t.remove()
            if chosen:
                break
        if not chosen:                     # nowhere clear: default spot, still readable thanks to the outline
            t = ax.annotate(bank['name'], xy, xytext=(9, -7), ha='left', va='center', **style)
            chosen = (t, t.get_window_extent(renderer), (9, -7))
        t, box, off = chosen
        t.set_path_effects([pe.withStroke(linewidth=2.6, foreground=stroke)])
        if abs(off[0]) > 12 or abs(off[1]) > 18:
            ax.annotate('', xy, xytext=off, textcoords='offset points', zorder=zorder - 1,
                        arrowprops=dict(arrowstyle='-', color=color, lw=0.6, alpha=0.8, shrinkA=0, shrinkB=4))
        taken.append(box)
