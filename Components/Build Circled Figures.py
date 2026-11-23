# MenuTitle: Build Circled Figures
# -*- coding: utf-8 -*-
"""Build circled (⓪–⑨) and black circled (⓿–❾) figures from the .numr figures.

All masters. Digits are centred on the _center anchor of whiteCircle and
blackCircle. Circled figures are components (whiteCircle + digit.numr), so they
follow later edits. Black circled figures are outlines with the digits cut out of
blackCircle, so rerun the script after changing the numerators.
whiteCircle and blackCircle are only drawn when missing or empty, unless
“Redraw” is checked. The ring weight matches the stem of zero.numr.
"""

import json
import traceback

import objc
from Foundation import NSMutableArray
from GlyphsApp import Glyphs, GSGlyph, GSPath, GSNode, GSAnchor, GSComponent, Message
from vanilla import FloatingWindow, TextBox, EditText, CheckBox, Button


TITLE = "Build Circled Figures"
PREF = "com.officeofpersonalresponsibility.circledFigures.v2"
PathOperator = objc.lookUpClass("GSPathOperator")
DIGITS = "zero one two three four five six seven eight nine".split()
KAPPA = 0.5522847498
ANCHOR = "_center"
WHITE, BLACK = ("whiteCircle", 0x25CB), ("blackCircle", 0x25CF)
# Unicode values of ⓪①…⑨ and ⓿❶…❾.
CIRCLED = [0x24EA] + [0x2460 + i for i in range(9)]
BLACK_CIRCLED = [0x24FF] + [0x2776 + i for i in range(9)]


def circle_path(cx, cy, r):
    k = r * KAPPA
    points = [
        ((cx + r, cy + k), "offcurve"), ((cx + k, cy + r), "offcurve"), ((cx, cy + r), "curve"),
        ((cx - k, cy + r), "offcurve"), ((cx - r, cy + k), "offcurve"), ((cx - r, cy), "curve"),
        ((cx - r, cy - k), "offcurve"), ((cx - k, cy - r), "offcurve"), ((cx, cy - r), "curve"),
        ((cx + k, cy - r), "offcurve"), ((cx + r, cy - k), "offcurve"), ((cx + r, cy), "curve"),
    ]
    path = GSPath()
    for position, kind in points:
        node = GSNode(position, kind)
        node.smooth = kind == "curve"
        path.nodes.append(node)
    path.closed = True
    return path


def center(bounds):
    return (bounds.origin.x + bounds.size.width / 2, bounds.origin.y + bounds.size.height / 2)


def stem(layer):
    """Horizontal thickness of the left side of a zero at half its height."""
    bounds = layer.bounds
    y = center(bounds)[1]
    xs = sorted(p.x for p in layer.intersectionsBetweenPoints(
        (bounds.origin.x - 10, y), (bounds.origin.x + bounds.size.width + 10, y)))[1:-1]
    return xs[1] - xs[0] if len(xs) >= 4 else None


class CircledFigures:
    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            Message(TITLE, "Open a font first.")
            return
        try:
            saved = json.loads(self.font.userData[PREF] or "{}")
        except (TypeError, ValueError):
            saved = {}
        cap = self.font.masters[0].capHeight or 700
        diameter = saved.get("diameter", int(round(cap * 1.2 / 5) * 5))
        sidebearing = saved.get("sidebearing", 40)

        self.w = FloatingWindow((320, 190), TITLE)
        self.w.redraw = CheckBox((15, 12, -15, 22), "Redraw whiteCircle and blackCircle",
                                 value=saved.get("redraw", False))
        self.w.diameterLabel = TextBox((35, 45, 150, 20), "Circle diameter")
        self.w.diameter = EditText((200, 42, -15, 22), format(diameter, "g"))
        self.w.sidebearingLabel = TextBox((35, 73, 150, 20), "Sidebearings")
        self.w.sidebearing = EditText((200, 70, -15, 22), format(sidebearing, "g"))
        self.w.note = TextBox((15, 102, -15, 44),
            "Missing circles are always drawn with these settings, centred on half the cap height. "
            "Figures 0–9 are always rebuilt.", sizeStyle="small")
        self.w.cancel = Button((15, -37, 95, 22), "Cancel", callback=lambda s: self.w.close())
        self.w.run = Button((-135, -37, 120, 22), "Build", callback=self.run)
        self.w.setDefaultButton(self.w.run)
        self.w.open()
        self.w.makeKey()

    def settings(self):
        values = dict(redraw=bool(self.w.redraw.get()))
        for key, label in (("diameter", "the circle diameter"), ("sidebearing", "the sidebearings")):
            try:
                values[key] = float(getattr(self.w, key).get().strip().replace("−", "-"))
            except ValueError:
                raise ValueError("Enter a number for %s." % label)
        if values["diameter"] <= 0:
            raise ValueError("The circle diameter must be positive.")
        return values

    # Lookup

    def find(self, name, unicode):
        glyph = self.font.glyphs[name]
        if glyph is None:
            code = "%04X" % unicode
            glyph = next((g for g in self.font.glyphs if code in (g.unicodes or ())), None)
        return glyph

    def find_or_create(self, name, unicode):
        glyph = self.find(name, unicode)
        if glyph is None:
            self.font.glyphs.append(GSGlyph(name))
            glyph = self.font.glyphs[name]
            if not glyph.unicode:
                glyph.unicode = "%04X" % unicode
        return glyph

    def numr(self, digit, master):
        glyph = self.font.glyphs[digit + ".numr"]
        layer = glyph.layers[master.id] if glyph is not None else None
        if layer is None or layer.bounds.size.width <= 0:
            raise ValueError("%s.numr is missing or empty in master %s." % (digit, master.name))
        return layer

    @staticmethod
    def anchor_position(glyph, master):
        layer = glyph.layers[master.id]
        anchor = layer.anchors[ANCHOR]
        if anchor is None:
            # Add the anchor to a hand-drawn circle that lacks one.
            anchor = GSAnchor(ANCHOR, center(layer.bounds))
            layer.anchors[ANCHOR] = anchor
            print("Added %s to %s (%s) at its centre." % (ANCHOR, glyph.name, master.name))
        return anchor.position.x, anchor.position.y

    def offset(self, digit, master, anchor):
        """Translation that puts the digit’s centre on the anchor.

        Horizontal: the digit’s own outline. Vertical: zero.numr, so that all
        digits share one baseline.
        """
        x = center(self.numr(digit, master).bounds)[0]
        y = center(self.numr("zero", master).bounds)[1]
        return anchor[0] - x, anchor[1] - y

    # Building

    @staticmethod
    def reset(glyph, layer, width):
        for key in ("leftMetricsKey", "rightMetricsKey", "widthMetricsKey"):
            setattr(glyph, key, None)
            setattr(layer, key, None)
        layer.hints = []
        layer.shapes = []
        layer.width = width

    def draw_circle(self, glyph, s, filled):
        width = s["diameter"] + 2 * s["sidebearing"]
        r = s["diameter"] / 2
        for master in self.font.masters:
            cx, cy = s["sidebearing"] + r, round(master.capHeight / 2)
            layer = glyph.layers[master.id]
            self.reset(glyph, layer, width)
            layer.shapes.append(circle_path(cx, cy, r))
            if not filled:
                weight = stem(self.numr("zero", master).copyDecomposedLayer())
                if weight is None:
                    weight = (list(master.stems or []) or [80])[0]
                layer.shapes.append(circle_path(cx, cy, r - min(weight, r - 1)))
            layer.correctPathDirection()
            layer.roundCoordinates()
            layer.anchors[ANCHOR] = GSAnchor(ANCHOR, (cx, cy))

    def build_circled(self, glyph, digit, ring):
        for master in self.font.masters:
            anchor = self.anchor_position(ring, master)
            dx, dy = self.offset(digit, master, anchor)
            layer = glyph.layers[master.id]
            self.reset(glyph, layer, ring.layers[master.id].width)
            base = GSComponent(ring.name)
            layer.shapes.append(base)
            base.automaticAlignment = False
            figure = GSComponent(digit + ".numr")
            layer.shapes.append(figure)
            figure.automaticAlignment = False
            figure.position = (dx, dy)

    def build_black(self, glyph, digit, disc_glyph):
        for master in self.font.masters:
            anchor = self.anchor_position(disc_glyph, master)
            dx, dy = self.offset(digit, master, anchor)
            disc = disc_glyph.layers[master.id].copyDecomposedLayer()
            shapes = NSMutableArray.array()
            for path in disc.paths:
                shapes.addObject_(path.copy())
            figure = self.numr(digit, master).copyDecomposedLayer()
            figure.removeOverlap()
            cutters = NSMutableArray.array()
            for path in figure.paths:
                path = path.copy()
                path.applyTransform((1, 0, 0, 1, dx, dy))
                cutters.addObject_(path)
            if not PathOperator.subtractPaths_from_error_(cutters, shapes, None)[0]:
                raise RuntimeError("Could not cut %s.numr out of %s (%s)." %
                                   (digit, disc_glyph.name, master.name))
            layer = glyph.layers[master.id]
            self.reset(glyph, layer, disc.width)
            for path in shapes:
                layer.shapes.append(path)
            layer.correctPathDirection()
            layer.roundCoordinates()

    def run(self, sender):
        try:
            self.w.getNSWindow().makeFirstResponder_(None)
            if Glyphs.font != self.font:
                raise ValueError("Return to the font this window was opened for, or reopen the script.")
            s = self.settings()
            # Check every numerator in every master before anything changes.
            for master in self.font.masters:
                for digit in DIGITS:
                    self.numr(digit, master)
            self.font.userData[PREF] = json.dumps(s)
        except ValueError as error:
            Message(TITLE, str(error))
            return

        built = []
        self.font.disableUpdateInterface()
        try:
            circles = {}
            for (name, unicode), filled in ((WHITE, False), (BLACK, True)):
                glyph = self.find_or_create(name, unicode)
                circles[name] = glyph
                if s["redraw"] or not any(len(layer.shapes) for layer in glyph.layers):
                    glyph.beginUndo()
                    try:
                        self.draw_circle(glyph, s, filled)
                    finally:
                        glyph.endUndo()
                    built.append(glyph.name)

            for i, digit in enumerate(DIGITS):
                for suffix, codes, build, base in (
                        (".circled", CIRCLED, self.build_circled, circles["whiteCircle"]),
                        (".blackCircled", BLACK_CIRCLED, self.build_black, circles["blackCircle"])):
                    glyph = self.find_or_create(digit + suffix, codes[i])
                    glyph.beginUndo()
                    try:
                        build(glyph, digit, base)
                    finally:
                        glyph.endUndo()
                    built.append(glyph.name)
        except Exception:
            Glyphs.showMacroWindow()
            print(traceback.format_exc())
            Message(TITLE, "Building stopped partway; see the Macro Panel. "
                           "Rebuilt glyphs can be undone per glyph.")
            return
        finally:
            self.font.enableUpdateInterface()

        self.font.newTab("".join("/" + name for name in built))
        Glyphs.showNotification(TITLE, "Built %d glyphs." % len(built))
        self.w.close()


if __name__ == "__main__":
    circledFiguresWindow = CircledFigures()
