# MenuTitle: Build Small Figure Components
# -*- coding: utf-8 -*-
"""Build existing small digits from a chosen source set, with per-set Y offsets.

Master layers only. Source outlines, special layers, backgrounds, anchors and
metric keys are preserved. Target shapes and their hints are replaced. No glyphs
are created. Positive offsets move up; offsets are absolute, never cumulative.
"""

import json
import math
import re
import traceback
from contextlib import contextmanager
import objc
from AppKit import NSApplication, NSShiftKeyMask
from vanilla.vanillaEditText import VanillaEditTextDelegate

from GlyphsApp import Glyphs, GSComponent, Message
from vanilla import FloatingWindow, TextBox, PopUpButton, EditText, CheckBox, Button


TITLE = "Build Small Figure Components"
PREF = "com.officeofpersonalresponsibility.smallFigureComponents.v1"
GROUPS = ("numr", "dnom", "inferior", "superior")
LABELS = ("Numerators (.numr)", "Denominators (.dnom)",
          "Inferiors (inferior / .subs)", "Superiors (superior / .sups)")
DIGITS = "zero one two three four five six seven eight nine".split()
PATTERN = re.compile(
    r"^(" + "|".join(DIGITS) + r")(inferior|superior)?((?:\.[A-Za-z0-9_-]+)*)$"
)
ALIASES = {"numr": "numr", "dnom": "dnom", "subs": "inferior",
           "sups": "superior", "inferior": "inferior", "superior": "superior"}


def identify(name):
    """Match digits only; keep other suffixes as part of the counterpart key."""
    match = PATTERN.match(name)
    if not match:
        return None
    digit, joined, suffix = match.groups()
    parts = suffix.split(".")[1:]
    markers = ([joined] if joined else []) + [ALIASES[p] for p in parts if p in ALIASES]
    if len(markers) != 1:
        return None
    return markers[0], (digit, tuple(p for p in parts if p not in ALIASES))


def number(value):
    result = float(str(value).strip().replace("−", "-"))
    if not math.isfinite(result):
        raise ValueError("Offsets must be finite numbers.")
    return result


def mappings(font, source_group):
    sources = {}
    for glyph in font.glyphs:
        info = identify(glyph.name)
        if info and info[0] == source_group:
            sources.setdefault(info[1], []).append(glyph.name)
    rows, skipped = [], []
    for glyph in font.glyphs:
        info = identify(glyph.name)
        if not info or info[0] == source_group:
            continue
        candidates = sources.get(info[1], [])
        if len(candidates) != 1:
            skipped.append("%s: %s source counterpart" % (
                glyph.name, "missing" if not candidates else "ambiguous"))
            continue
        rows.append(dict(target=glyph.name, source=candidates[0], group=info[0]))
    return sorted(rows, key=lambda row: row["target"]), skipped


def check_cycles(font, rows):
    # Keep existing edges too: a source must not depend on a target being erased.
    graph = {g.name: {c.componentName for layer in g.layers for c in layer.components}
             for g in font.glyphs}
    for row in rows:
        graph[row["target"]].add(row["source"])
    def reaches(start, target):
        stack, seen = [start], set()
        while stack:
            name = stack.pop()
            if name == target:
                return True
            if name not in seen:
                seen.add(name)
                stack.extend(graph.get(name, ()))
        return False
    for row in rows:
        if reaches(row["source"], row["target"]):
            raise ValueError("Component cycle: %s depends on %s. Choose an independent "
                             "source set or decompose that source first." %
                             (row["source"], row["target"]))


def plan_layers(font, rows, masters):
    check_cycles(font, rows)
    plan = []
    for row in rows:
        for master in masters:
            source = font.glyphs[row["source"]].layers[master.id]
            target = font.glyphs[row["target"]].layers[master.id]
            if source is None or target is None or not len(source.shapes):
                raise ValueError("Missing or empty master layer: %s → %s (%s). "
                                 "No layers have been changed." %
                                 (row["source"], row["target"], master.name))
            plan.append((row, target, source))
    return plan


class SmallFigureOffsetDelegate(VanillaEditTextDelegate):
    @objc.signature(b"Z@:@@:")
    def control_textView_doCommandBySelector_(self, control, editor, selector):
        command = selector.decode("ascii") if isinstance(selector, bytes) else str(selector)
        directions = {"moveUp:": 1, "moveDown:": -1,
                      "moveUpAndModifySelection:": 1, "moveDownAndModifySelection:": -1}
        if command not in directions:
            return False
        try:
            value = number(editor.string())
        except ValueError:
            # Let an empty or unfinished numeric entry start at zero.
            value = 0.0
        event = NSApplication.sharedApplication().currentEvent()
        shift = event is not None and bool(event.modifierFlags() & NSShiftKeyMask)
        value += directions[command] * (10 if shift else 1)
        text = format(value, ".12g")
        control.setStringValue_(text)
        editor.setString_(text)
        editor.setSelectedRange_((0, len(text)))
        self.action_(control)
        return True


class SmallFigureOffsetEditText(EditText):
    nsTextFieldDelegateClass = SmallFigureOffsetDelegate


class SmallFigureComponents:
    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            Message(TITLE, "Open a font first.")
            return
        try:
            self.settings = json.loads(self.font.userData[PREF] or "{}")
        except (TypeError, ValueError):
            self.settings = {}
        self.source = self.settings.get("source", "numr")
        if self.source not in GROUPS:
            self.source = "numr"
        self.preview_layers = []
        self.busy = True
        self.closed = False
        self.w = FloatingWindow((430, 405), TITLE)
        self.w.sourceLabel = TextBox((15, 18, 105, 20), "Base shape set:")
        self.w.source = PopUpButton((125, 15, -15, 24), LABELS, callback=self.change_source)
        self.w.source.set(GROUPS.index(self.source))
        self.w.info = TextBox((15, 52, -15, 32),
            "Set each target’s Y offset relative to the source, in font units.\n"
            "↑ / ↓ changes Y by 1; Shift + ↑ / ↓ changes it by 10.", sizeStyle="small")
        self.w.yLabel = TextBox((325, 91, 90, 18), "Y offset", sizeStyle="small")
        for i, group in enumerate(GROUPS):
            y = 112 + i * 28
            setattr(self.w, "use_" + group, CheckBox((15, y, 295, 22), LABELS[i],
                value=True, callback=self.refresh))
            setattr(self.w, "y_" + group, SmallFigureOffsetEditText((325, y, 90, 22), "0", callback=self.refresh, continuous=True))
        self.w.allMasters = CheckBox((15, 231, -15, 22), "Apply to all masters", value=True, callback=self.refresh)
        self.w.live = CheckBox((15, 259, 190, 22), "Live preview", value=True,
                               callback=self.refresh)
        self.w.showPreview = Button((-160, 258, 145, 24), "Show preview", callback=self.show_preview)
        self.w.note = TextBox((15, 294, -15, 32),
            "Preview updates your existing layers. Cancel restores them.\n"
            "Positive Y moves up; automatic alignment stays on.", sizeStyle="small")
        self.w.status = TextBox((15, 333, -15, 30), "", sizeStyle="small")
        self.w.cancel = Button((15, 373, 95, 22), "Cancel", callback=self.cancel)
        self.w.run = Button((-190, 373, 175, 22), "Build components", callback=self.run)
        self.w.bind("close", self.window_closed)
        self.load_set()
        self.w.open()
        self.busy = False
        self.refresh()
        self.w.makeKey()

    def set_settings(self):
        return self.settings.setdefault(self.source, {})

    def capture(self):
        saved = self.set_settings()
        saved["offsets"] = {g: getattr(self.w, "y_" + g).get() for g in GROUPS}
        saved["enabled"] = {g: bool(getattr(self.w, "use_" + g).get()) for g in GROUPS}
        # Old per-glyph overrides must not silently affect the simplified controls.
        saved.pop("overrides", None)

    def load_set(self):
        saved = self.set_settings()
        for group in GROUPS:
            getattr(self.w, "y_" + group).set(saved.get("offsets", {}).get(group, "0"))
            getattr(self.w, "use_" + group).set(saved.get("enabled", {}).get(group, True))
            getattr(self.w, "use_" + group).enable(group != self.source)
            getattr(self.w, "y_" + group).enable(group != self.source)
        if not self.busy:
            self.refresh()

    def change_source(self, sender):
        self.capture()
        self.source = GROUPS[self.w.source.get()]
        self.load_set()

    def refresh(self, sender=None):
        if self.busy or self.closed:
            return
        self.capture()
        rows, self.skipped = mappings(self.font, self.source)
        saved = self.set_settings()
        display = []
        for row in rows:
            if saved["enabled"][row["group"]]:
                row["default"] = saved["offsets"][row["group"]]
                display.append(row)
        self.rows = display
        self.w.status.set("%d target glyphs.\n%d missing or ambiguous counterparts." %
                          (len(display), len(self.skipped)))
        if self.w.live.get():
            self.update_preview()
        else:
            self.close_preview()

    def parsed_rows(self):
        rows = [dict(row) for row in self.rows]
        for row in rows:
            try:
                row["y"] = number(row["default"])
            except ValueError:
                raise ValueError("Enter a numeric Y offset for the %s set." % row["group"])
        return rows

    def masters(self):
        if self.w.allMasters.get():
            return list(self.font.masters)
        master_id = (self.font.selectedLayers[0].master if self.font.selectedLayers else self.font.selectedFontMaster).id
        return [m for m in self.font.masters if m.id == master_id]

    @staticmethod
    def place(row, layer):
        component = GSComponent(row["source"])
        layer.hints = []
        layer.shapes = [component]
        component.transform = (1, 0, 0, 1, 0, row["y"])
        component.automaticAlignment = True
        component.alignment = 3
        layer.alignComponents()

    @contextmanager
    def preview_edit(self, layers):
        # Preview and restoration must not add steps to the normal Undo history.
        managers = []
        self.font.disableUpdateInterface()
        try:
            for layer in layers:
                manager = layer.parent.undoManager()
                if manager is not None and manager not in managers:
                    manager.disableUndoRegistration()
                    managers.append(manager)
            yield
        finally:
            for manager in reversed(managers):
                manager.enableUndoRegistration()
            self.font.enableUpdateInterface()

    @staticmethod
    def restore_layer(layer, backup):
        # Copy the whole layer together so hint-to-node references remain intact.
        original = backup.copy()
        layer.hints = []
        layer.shapes = list(original.shapes)
        layer.hints = list(original.hints)
        layer.width = original.width

    def close_preview(self):
        if not self.preview_layers:
            return
        with self.preview_edit([layer for layer, _ in self.preview_layers]):
            for layer, backup in self.preview_layers:
                self.restore_layer(layer, backup)
        self.preview_layers = []
        Glyphs.redraw()

    def update_preview(self):
        if Glyphs.font != self.font:
            self.w.status.set("Return to the font this window was opened for.")
            return
        try:
            rows = self.parsed_rows()
            masters = self.masters()
            # Remove the previous preview before checking dependencies or changing scope.
            self.close_preview()
            plan = plan_layers(self.font, rows, masters)
            self.preview_layers = [(layer, layer.copy()) for _, layer, _ in plan]
            with self.preview_edit([layer for _, layer, _ in plan]):
                for row, layer, _ in plan:
                    self.place(row, layer)
            Glyphs.redraw()
            if self.font.currentTab is not None:
                self.font.currentTab.redraw()
            self.w.status.set("Live preview: %d targets. %d unmatched." % (len(rows), len(self.skipped)))
        except ValueError as error:
            # Keep the last valid preview while a number is being typed.
            self.w.status.set(str(error))
        except Exception:
            print(traceback.format_exc())
            self.close_preview()
            self.w.status.set("Preview failed. Original layers restored; see Macro Panel.")

    def show_preview(self, sender):
        self.w.live.set(True)
        self.refresh()
        Glyphs.redraw()

    def cancel(self, sender):
        self.w.close()

    def window_closed(self, sender):
        self.closed = True
        self.close_preview()


    def run(self, sender):
        try:
            # Commit the active offset field before reading its value.
            self.w.getNSWindow().makeFirstResponder_(None)
            if Glyphs.font != self.font:
                raise ValueError("Return to the font this window was opened for, or reopen the script.")
            self.refresh()
            rows = self.parsed_rows()
            if not rows:
                raise ValueError("No matching target glyphs. Choose another source or enable a target set.")
            masters = self.masters()
            # Reapply once with Undo enabled, starting from the original layers.
            self.close_preview()
            plan = plan_layers(self.font, rows, masters)
            self.settings["source"] = self.source
            self.font.userData[PREF] = json.dumps(self.settings)
            # Snapshot only data this script changes, for rollback on an API error.
            snapshots = [(layer, layer.copy()) for _, layer, _ in plan]
            glyphs = [self.font.glyphs[row["target"]] for row in rows]
            begun = []
            self.font.disableUpdateInterface()
            try:
                for glyph in glyphs:
                    glyph.beginUndo()
                    begun.append(glyph)
                for row, layer, source in plan:
                    self.place(row, layer)

            except Exception:
                for layer, backup in snapshots:
                    self.restore_layer(layer, backup)
                raise
            finally:
                for glyph in reversed(begun):
                    glyph.endUndo()
                self.font.enableUpdateInterface()
            for message in self.skipped:
                print("Skipped " + message)
            for row in rows:
                print("%s ← %s, Y = %g" % (row["target"], row["source"], row["y"]))
            Glyphs.redraw()
            result = "Built %d glyphs across %d master(s), %d layers." % (len(rows), len(masters), len(plan))
            self.w.status.set(result)
            Glyphs.showNotification(TITLE, result)
            self.w.close()
        except ValueError as error:
            Message(TITLE, str(error))
        except Exception:
            Glyphs.showMacroWindow()
            print(traceback.format_exc())
            Message(TITLE, "The operation failed. Changed layers were restored if editing had begun. See the Macro Panel.")


if __name__ == "__main__":
    smallFigureComponentsWindow = SmallFigureComponents()
