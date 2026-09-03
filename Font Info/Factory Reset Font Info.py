# MenuTitle: Factory Reset Font Metadata
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
from Foundation import NSDate

font = Glyphs.font

if font is None:
    print("No font open.")

else:
    font.disableUpdateInterface()

    try:
        familyName = font.familyName

        # --------------------------------------------------
        # FONT LEVEL
        # --------------------------------------------------

        # Remove all optional font properties
        for prop in list(font.properties):
            try:
                font.removeObjectFromProperties_(prop)
            except Exception as e:
                print("Could not remove font property:", e)

        # Restore main Family Name
        font.familyName = familyName

        # Remove all font custom parameters
        font.customParameters = []


        # --------------------------------------------------
        # MASTER LEVEL
        # --------------------------------------------------

        for master in font.masters:
            master.customParameters = []


        # --------------------------------------------------
        # INSTANCE / EXPORT LEVEL
        # --------------------------------------------------

        for instance in font.instances:

            # Keep actual Style Name
            styleName = instance.name

            # Remove custom export parameters
            instance.customParameters = []

            # Remove optional instance properties
            try:
                for prop in list(instance.properties):
                    try:
                        instance.removeObjectFromProperties_(prop)
                    except Exception as e:
                        print(
                            "Could not remove instance property:",
                            getattr(prop, "key", prop),
                            e
                        )
            except Exception as e:
                print("Could not access instance properties:", e)

            # Restore Style Name
            instance.name = styleName


        # --------------------------------------------------
        # VERSION / DATE
        # --------------------------------------------------

        font.versionMajor = 1
        font.versionMinor = 0

        try:
            font.date = NSDate.date()
        except Exception:
            pass


        # --------------------------------------------------
        # REPORT
        # --------------------------------------------------

        print("\nFactory reset complete.")
        print("Family Name:", font.familyName)

        print("\nRemaining font properties:")
        for prop in font.properties:
            print("•", getattr(prop, "key", prop))

        print("\nInstances:")
        for instance in font.instances:
            print("•", instance.name)

            try:
                print("  properties:",
                      [getattr(p, "key", p) for p in instance.properties])
            except:
                pass

            print("  custom parameters:",
                  len(instance.customParameters))

    finally:
        font.enableUpdateInterface()