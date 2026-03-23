#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import polib
from deep_translator import GoogleTranslator


def it():
    # Load your .po file
    po = polib.pofile("beehive_it.po")

    # Set up the translator
    translator = GoogleTranslator(source="en", target="it")

    # Translate each entry
    for entry in po:
        if entry.msgid and not entry.msgstr:
            try:
                translation = translator.translate(entry.msgid)
                entry.msgstr = translation
            except Exception:
                entry.msgstr = "[Translation Error]"

    # Save the translated .po file
    po.save("beehive_it.po")
    print("Translation completed. Saved as 'beehive_it.po'")


def en():
    # Load your .po file
    po = polib.pofile("beehive.pot")

    # dummy Translate each entry
    for entry in po:
        if entry.msgid and not entry.msgstr:
            try:
                entry.msgstr = entry.msgid
            except Exception:
                entry.msgstr = "[Translation Error]"

    # Save the translated .po file
    po.save("beehive_en.po")


it()
en()
