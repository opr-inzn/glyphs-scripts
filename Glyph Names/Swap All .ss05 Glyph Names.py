#MenuTitle: Swap All .ss05 Glyph Names

# -*- coding: utf-8 -*-

"""
Swap every final .ss05 glyph suffix with its unsuffixed counterpart.

Examples:
    period.ss05            <-> period
    Rcommaaccent.ss04.ss05 <-> Rcommaaccent.ss04
    f_f_j.liga.ss05       <-> f_f_j.liga
"""

import re


def transformed_metric_key(value, replacements):
    """Replace complete glyph-name references inside a metric-key formula."""
    if value is None:
        return None

    result = str(value)
    glyph_name_character = r"A-Za-z0-9_.-"

    for old_name in sorted(replacements, key=len, reverse=True):
        pattern = r"(?<![%s])%s(?![%s])" % (
            glyph_name_character,
            re.escape(old_name),
            glyph_name_character,
        )
        result = re.sub(pattern, replacements[old_name], result)

    return result


font = Glyphs.font

if font is None:

    Message("Open a font first.", title="Swap All .ss05 Glyph Names", OKButton=None)

else:

    suffix = ".ss05"
    glyphs_by_name = {glyph.name: glyph for glyph in font.glyphs}
    pairs = []
    missing = []

    for alternate in font.glyphs:
        alternate_name = alternate.name
        if not alternate_name.endswith(suffix):
            continue

        base_name = alternate_name[:-len(suffix)]
        base = glyphs_by_name.get(base_name)

        if base is None:
            missing.append(alternate_name)
            continue

        pairs.append((base, alternate, base_name, alternate_name))

    if not pairs:
        message = "No complete .ss05/base glyph pairs found."
        if missing:
            message += "\nMissing base glyphs:\n" + "\n".join(missing)
        Message(message, title="Swap All .ss05 Glyph Names", OKButton=None)

    else:

        metric_attributes = (
            "leftMetricsKey",
            "rightMetricsKey",
            "widthMetricsKey",
            "topMetricsKey",
            "bottomMetricsKey",
        )
        base_to_alternate = {pair[2]: pair[3] for pair in pairs}
        alternate_to_base = {pair[3]: pair[2] for pair in pairs}
        metric_states = []

        # Glyphs may rewrite name-based metric keys while glyphs are renamed.
        # Save them on their glyph objects, then adjust references to match each
        # object's new default or .ss05 name.
        for glyph in font.glyphs:
            glyph_values = {}
            for attribute in metric_attributes:
                if hasattr(glyph, attribute):
                    glyph_values[attribute] = getattr(glyph, attribute)

            layer_values = []
            for layer in glyph.layers:
                values = {}
                for attribute in metric_attributes:
                    if hasattr(layer, attribute):
                        values[attribute] = getattr(layer, attribute)
                layer_values.append((layer, values))

            metric_states.append((glyph, glyph.name, glyph_values, layer_values))

        existing_names = set(glyphs_by_name)
        temporary_names = []

        for index, pair in enumerate(pairs, start=1):
            temporary_name = "swapSS05Temp%03d" % index
            while temporary_name in existing_names:
                index += 1
                temporary_name = "swapSS05Temp%03d" % index
            existing_names.add(temporary_name)
            temporary_names.append(temporary_name)

        font.disableUpdateInterface()
        try:
            # Free all .ss05 names first so none of the swaps collide.
            for pair, temporary_name in zip(pairs, temporary_names):
                pair[1].name = temporary_name

            # Put the old .ss05 names on the base glyphs.
            for pair in pairs:
                pair[0].name = pair[3]

            # Put the old base names on the alternate glyphs.
            for pair, temporary_name in zip(pairs, temporary_names):
                pair[1].name = pair[2]
        finally:
            # Keep metric keys with each swapped glyph object, while changing
            # referenced names in the same direction as that glyph's name.
            for glyph, original_name, glyph_values, layer_values in metric_states:
                if original_name in base_to_alternate:
                    replacements = base_to_alternate
                elif original_name in alternate_to_base:
                    replacements = alternate_to_base
                else:
                    replacements = {}

                for attribute, value in glyph_values.items():
                    setattr(
                        glyph,
                        attribute,
                        transformed_metric_key(value, replacements),
                    )

                for layer, values in layer_values:
                    for attribute, value in values.items():
                        setattr(
                            layer,
                            attribute,
                            transformed_metric_key(value, replacements),
                        )

            font.enableUpdateInterface()

        print("Swapped %d .ss05 glyph pairs:" % len(pairs))
        for pair in pairs:
            print("%s ⇄ %s" % (pair[2], pair[3]))

        if missing:
            print("\nSkipped because the base glyph was missing:")
            for glyph_name in missing:
                print(glyph_name)

        Message(
            "Swapped %d .ss05 glyph pairs.%s"
            % (
                len(pairs),
                "\nSkipped %d missing base glyphs." % len(missing) if missing else "",
            ),
            title="Swap All .ss05 Glyph Names",
            OKButton=None,
        )
