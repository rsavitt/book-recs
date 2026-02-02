"""
Book title aliases for fuzzy matching in Reddit posts.

Common abbreviations and alternate names used by the r/romantasy community.
"""

# Book title aliases: alias -> canonical title
# Keys are lowercase for case-insensitive matching
BOOK_ALIASES: dict[str, str] = {
    # Sarah J. Maas - A Court of Thorns and Roses series
    "acotar": "A Court of Thorns and Roses",
    "a court of thorns and roses": "A Court of Thorns and Roses",
    "acomaf": "A Court of Mist and Fury",
    "a court of mist and fury": "A Court of Mist and Fury",
    "acowar": "A Court of Wings and Ruin",
    "a court of wings and ruin": "A Court of Wings and Ruin",
    "acofas": "A Court of Frost and Starlight",
    "acosf": "A Court of Silver Flames",
    "a court of silver flames": "A Court of Silver Flames",

    # Sarah J. Maas - Throne of Glass series
    "tog": "Throne of Glass",
    "throne of glass": "Throne of Glass",
    "com": "Crown of Midnight",
    "crown of midnight": "Crown of Midnight",
    "hof": "Heir of Fire",
    "heir of fire": "Heir of Fire",
    "qos": "Queen of Shadows",
    "queen of shadows": "Queen of Shadows",
    "eos": "Empire of Storms",
    "empire of storms": "Empire of Storms",
    "tod": "Tower of Dawn",
    "tower of dawn": "Tower of Dawn",
    "koa": "Kingdom of Ash",
    "kingdom of ash": "Kingdom of Ash",

    # Sarah J. Maas - Crescent City series
    "cc": "House of Earth and Blood",
    "cc1": "House of Earth and Blood",
    "hoeab": "House of Earth and Blood",
    "house of earth and blood": "House of Earth and Blood",
    "cc2": "House of Sky and Breath",
    "hosab": "House of Sky and Breath",
    "house of sky and breath": "House of Sky and Breath",
    "cc3": "House of Flame and Shadow",
    "hofas": "House of Flame and Shadow",
    "house of flame and shadow": "House of Flame and Shadow",
    "crescent city": "House of Earth and Blood",

    # Rebecca Yarros - Empyrean series
    "fourth wing": "Fourth Wing",
    "fw": "Fourth Wing",
    "iron flame": "Iron Flame",
    "if": "Iron Flame",
    "onyx storm": "Onyx Storm",

    # Carissa Broadbent - Crowns of Nyaxia series
    "serpent and wings": "The Serpent and the Wings of Night",
    "the serpent and the wings of night": "The Serpent and the Wings of Night",
    "tsatwon": "The Serpent and the Wings of Night",
    "ashes and the star cursed king": "The Ashes and the Star-Cursed King",
    "the ashes and the star-cursed king": "The Ashes and the Star-Cursed King",

    # Jennifer L. Armentrout - Blood and Ash series
    "fbaa": "From Blood and Ash",
    "from blood and ash": "From Blood and Ash",
    "akofaf": "A Kingdom of Flesh and Fire",
    "a kingdom of flesh and fire": "A Kingdom of Flesh and Fire",
    "tcogb": "The Crown of Gilded Bones",
    "the crown of gilded bones": "The Crown of Gilded Bones",
    "twotq": "The War of Two Queens",
    "the war of two queens": "The War of Two Queens",
    "blood and ash": "From Blood and Ash",

    # Scarlett St. Clair - Hades x Persephone
    "touch of darkness": "A Touch of Darkness",
    "a touch of darkness": "A Touch of Darkness",
    "atod": "A Touch of Darkness",
    "game of fate": "A Game of Fate",
    "a game of fate": "A Game of Fate",
    "touch of ruin": "A Touch of Ruin",
    "a touch of ruin": "A Touch of Ruin",
    "touch of malice": "A Touch of Malice",
    "a touch of malice": "A Touch of Malice",

    # Holly Black - Folk of the Air series
    "cruel prince": "The Cruel Prince",
    "the cruel prince": "The Cruel Prince",
    "tcp": "The Cruel Prince",
    "wicked king": "The Wicked King",
    "the wicked king": "The Wicked King",
    "twk": "The Wicked King",
    "queen of nothing": "The Queen of Nothing",
    "the queen of nothing": "The Queen of Nothing",
    "tqon": "The Queen of Nothing",
    "folk of the air": "The Cruel Prince",

    # Leigh Bardugo - Grishaverse
    "shadow and bone": "Shadow and Bone",
    "sab": "Shadow and Bone",
    "siege and storm": "Siege and Storm",
    "sas": "Siege and Storm",
    "ruin and rising": "Ruin and Rising",
    "rar": "Ruin and Rising",
    "six of crows": "Six of Crows",
    "soc": "Six of Crows",
    "crooked kingdom": "Crooked Kingdom",
    "ck": "Crooked Kingdom",
    "king of scars": "King of Scars",
    "kos": "King of Scars",
    "rule of wolves": "Rule of Wolves",
    "row": "Rule of Wolves",

    # Elise Kova - Air Awakens series
    "air awakens": "Air Awakens",
    "fire falling": "Fire Falling",
    "earth's end": "Earth's End",
    "water's wrath": "Water's Wrath",
    "crystal crowned": "Crystal Crowned",

    # Other popular romantasy
    "zodiac academy": "Zodiac Academy",
    "za": "Zodiac Academy",
    "the shadows between us": "The Shadows Between Us",
    "tstbu": "The Shadows Between Us",
    "shadows between us": "The Shadows Between Us",
    "daughter of no worlds": "Daughter of No Worlds",
    "donw": "Daughter of No Worlds",
    "kingmaker": "Kingmaker",
    "radiance": "Radiance",
    "bride": "Bride",
    "assistant to the villain": "Assistant to the Villain",
    "attv": "Assistant to the Villain",
    "powerless": "Powerless",
    "reckless": "Reckless",
    "ruthless vows": "Ruthless Vows",
    "divine rivals": "Divine Rivals",
    "dr": "Divine Rivals",
    "kingdom of the wicked": "Kingdom of the Wicked",
    "kotw": "Kingdom of the Wicked",
    "kingdom of the cursed": "Kingdom of the Cursed",
    "kotc": "Kingdom of the Cursed",
    "kingdom of the feared": "Kingdom of the Feared",
    "kotf": "Kingdom of the Feared",
    "the bridge kingdom": "The Bridge Kingdom",
    "tbk": "The Bridge Kingdom",
    "the traitor queen": "The Traitor Queen",
    "ttq": "The Traitor Queen",
    "shatter me": "Shatter Me",
    "hunting adeline": "Hunting Adeline",
    "haunting adeline": "Haunting Adeline",
    "ice planet barbarians": "Ice Planet Barbarians",
    "ipb": "Ice Planet Barbarians",
    "plated prisoner": "A Ruin of Roses",
    "gild": "Gild",
    "glint": "Glint",
    "gleam": "Gleam",
    "glow": "Glow",
    "gold": "Gold",
}


# Series name aliases: alias -> canonical series name
SERIES_ALIASES: dict[str, str] = {
    "acotar": "A Court of Thorns and Roses",
    "acotar series": "A Court of Thorns and Roses",
    "tog": "Throne of Glass",
    "tog series": "Throne of Glass",
    "cc": "Crescent City",
    "crescent city": "Crescent City",
    "blood and ash": "Blood and Ash",
    "fbaa": "Blood and Ash",
    "folk of the air": "Folk of the Air",
    "fota": "Folk of the Air",
    "grishaverse": "Grishaverse",
    "grisha": "Grishaverse",
    "empyrean": "Empyrean",
    "fourth wing series": "Empyrean",
    "crowns of nyaxia": "Crowns of Nyaxia",
    "nyaxia": "Crowns of Nyaxia",
    "kotw series": "Kingdom of the Wicked",
    "kingdom of the wicked series": "Kingdom of the Wicked",
    "za": "Zodiac Academy",
    "zodiac academy": "Zodiac Academy",
    "plated prisoner": "Plated Prisoner",
    "plated prisoner series": "Plated Prisoner",
}


def get_canonical_title(text: str) -> str | None:
    """
    Get the canonical book title from an alias or abbreviation.

    Args:
        text: The alias or abbreviation to look up

    Returns:
        Canonical title if found, None otherwise
    """
    normalized = text.lower().strip()
    return BOOK_ALIASES.get(normalized)


def get_canonical_series(text: str) -> str | None:
    """
    Get the canonical series name from an alias.

    Args:
        text: The alias to look up

    Returns:
        Canonical series name if found, None otherwise
    """
    normalized = text.lower().strip()
    return SERIES_ALIASES.get(normalized)
