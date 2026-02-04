"""
Seed phrases for vector-based trope classification.

Each trope has 3-5 natural-language phrases written as readers would describe them
in book reviews. These are embedded with sentence-transformers and used as centroids
for cosine similarity scoring against book review embeddings.

Trope slugs match the existing BookTag.slug values in app/data/tags.py.
"""

# Per-trope similarity threshold overrides (default is 0.45 from config)
TROPE_THRESHOLD_OVERRIDES: dict[str, float] = {
    # Broader tropes need higher thresholds to avoid false positives
    "romance": 0.55,
    "fantasy": 0.55,
    # Very specific tropes can use lower thresholds
    "dragon-riders": 0.40,
    "fated-mates": 0.40,
    "only-one-bed": 0.40,
    "who-did-this-to-you": 0.40,
    "why-choose": 0.42,
}

TROPE_SEEDS: dict[str, list[str]] = {
    # === ROMANCE TROPES ===
    "enemies-to-lovers": [
        "The romance builds from hatred and antagonism, they start as enemies and fall in love.",
        "I love how these two despised each other at first, the banter and tension before they finally gave in.",
        "Classic enemies to lovers where they can't stand each other but the chemistry is undeniable.",
        "Their rivalry slowly transforms into passion, the hate-to-love arc was perfectly executed.",
    ],
    "slow-burn": [
        "The romance builds so slowly over hundreds of pages, but the payoff is worth the wait.",
        "This is a slow burn romance where the tension simmers for the entire book.",
        "I loved how gradually the romantic feelings developed, nothing was rushed.",
        "The slow burn in this book had me screaming, the longing and anticipation just kept building.",
    ],
    "found-family": [
        "The group of misfits coming together and forming their own family was so heartwarming.",
        "I loved the found family dynamic, these characters become each other's home.",
        "The found family trope is strong here, they protect and care for each other like siblings.",
        "The friendships and chosen family bonds were just as compelling as the romance.",
    ],
    "forced-proximity": [
        "They're forced to be near each other, trapped together, and feelings develop.",
        "The forced proximity trope is done so well, being stuck together makes the tension unbearable.",
        "Thrown together by circumstance, forced to share space, the proximity makes sparks fly.",
        "I love when characters who hate each other are forced into close quarters.",
    ],
    "forbidden-love": [
        "Their love is forbidden, they shouldn't be together but can't stay apart.",
        "The forbidden romance between them added so much tension and stakes.",
        "Star-crossed lovers who risk everything to be together despite the consequences.",
        "The forbidden aspect of their relationship made every stolen moment more intense.",
    ],
    "friends-to-lovers": [
        "Best friends who realize they've been in love with each other all along.",
        "The friends to lovers transition was so natural and sweet.",
        "I love when childhood friends develop romantic feelings, the familiarity makes it special.",
        "Watching their friendship evolve into something more was beautifully done.",
    ],
    "fated-mates": [
        "They're fated mates, destined to be together by some supernatural bond.",
        "The mate bond between them was intense, they could feel each other's emotions.",
        "I love the fated mates trope, the pull between them was magnetic.",
        "When they discover they're mates, the bond is undeniable and all-consuming.",
        "The mating bond snapped into place and everything changed between them.",
    ],
    "grumpy-sunshine": [
        "One is grumpy and brooding, the other is bright and optimistic, they balance each other.",
        "The grumpy sunshine dynamic was adorable, she melted his cold exterior.",
        "He's all scowls and walls, she's all warmth and light, together they're perfect.",
        "I love the contrast between the brooding love interest and the cheerful protagonist.",
    ],
    "morally-grey": [
        "The love interest is morally grey, he does terrible things but you root for him anyway.",
        "Complex characters with questionable morals, neither purely good nor evil.",
        "The morally grey hero made dark choices but his devotion to her was unwavering.",
        "I love a villain love interest, he's ruthless to everyone except her.",
        "Antihero protagonist who walks the line between darkness and redemption.",
    ],
    "touch-her-and-die": [
        "He would burn the world for her, protective and possessive to an extreme.",
        "The 'touch her and die' energy was intense, he destroyed anyone who threatened her.",
        "His protective instincts were feral, no one could even look at her wrong.",
        "The possessive alpha male who would kill for her without hesitation.",
    ],
    "he-falls-first": [
        "He fell first and he fell harder, pining for her while she was oblivious.",
        "The male love interest was completely gone for her before she even noticed.",
        "I love when the hero falls first, watching him pine and worship her was everything.",
        "He was in love with her long before she realized her own feelings.",
    ],
    "only-one-bed": [
        "There was only one bed and they had to share it, the tension was palpable.",
        "The classic one bed trope, forced to sleep next to each other with all that tension.",
        "Sharing a bed when they're trying to ignore their attraction was delicious.",
    ],
    "fake-dating": [
        "They pretend to be in a relationship, fake dating that turns into real feelings.",
        "The fake relationship becomes real as they catch genuine feelings for each other.",
        "Fake engagement trope where playing pretend leads to actual love.",
    ],
    "marriage-of-convenience": [
        "Married for political alliance or convenience, slowly falling in love with their spouse.",
        "An arranged marriage where neither wanted it but they grow to love each other.",
        "Marriage of convenience trope, they wed for duty but discover real passion.",
        "The political marriage slowly becomes a love match as they get to know each other.",
    ],
    "who-did-this-to-you": [
        "When he sees she's been hurt, his rage is terrifying and his tenderness is devastating.",
        "The 'who did this to you' moment when he discovers someone hurt her was so intense.",
        "His fury at seeing her injured was primal, then he gently tended to her wounds.",
        "The protective rage followed by gentle care, that contrast destroyed me.",
    ],
    "why-choose": [
        "She doesn't choose between her love interests, she keeps them all.",
        "Why choose when you can have multiple love interests, reverse harem done right.",
        "The polyamorous relationship dynamic where she loves all of them equally.",
        "Multiple male love interests who all adore her and she doesn't have to pick just one.",
        "A reverse harem romance where every love interest brings something different.",
    ],
    "love-triangle": [
        "Torn between two love interests, a love triangle that kept me guessing.",
        "The love triangle had me switching teams with every chapter.",
        "Two people competing for the protagonist's heart, each compelling in different ways.",
    ],
    # === SETTING TROPES ===
    "fae": [
        "Set in a world of fae courts, with beautiful and dangerous faerie creatures.",
        "The fae world-building was incredible, with courts of light and dark.",
        "Faerie politics and deadly beautiful fae warriors dominate this story.",
        "The fae realm with its bargains, glamour, and ancient magic was enchanting.",
        "A high fae love interest with pointed ears and centuries of power.",
    ],
    "dragons": [
        "Dragons are central to the story, majestic fire-breathing creatures.",
        "The dragon lore and world-building with dragon shifters was fantastic.",
        "Dragons soaring through the skies, bonded to their riders or terrorizing kingdoms.",
        "A world where dragons are revered, feared, and integral to the magic system.",
    ],
    "dragon-riders": [
        "Dragon riders training at a war college, bonding with their dragons.",
        "The academy where riders are chosen by their dragons and train for war.",
        "Dragon rider school where survival isn't guaranteed and the bond is everything.",
        "Characters who ride dragons into battle, the rider-dragon bond is central.",
    ],
    "vampires": [
        "Vampire romance with blood drinking, immortality, and dark seduction.",
        "The vampire love interest is centuries old, powerful, and dangerously alluring.",
        "Blood bonds and vampire courts, immortal romance with dark undertones.",
        "A world of vampires with their own hierarchy, politics, and supernatural allure.",
    ],
    "shifters": [
        "Shapeshifter romance with werewolves or other animal shifters.",
        "The wolf shifter pack dynamics and mate bonds drove the plot.",
        "Shifters who transform between human and animal form, with pack hierarchy.",
        "Werewolf romance with alpha dynamics, the shift, and primal instincts.",
    ],
    "witches": [
        "Witches and witchcraft are central, with covens and magical abilities.",
        "A witch heroine discovering her powers, spells and potions and covens.",
        "Witchy vibes with herbalism, spell-casting, and magical communities.",
    ],
    "magic-academy": [
        "Set in a magical academy where students learn sorcery and combat.",
        "Magic school setting with classes, rivalries, and forbidden areas to explore.",
        "A fantasy academy where young mages train their powers and navigate social hierarchies.",
        "The academy setting with magical training, tournaments, and dangerous tests.",
    ],
    "royal-court": [
        "Set in a royal court with princes, queens, political scheming, and courtly intrigue.",
        "Court politics and royal machinations drive the plot, with balls and betrayals.",
        "A world of kingdoms and royal courts where power games determine everything.",
        "The royal court setting with its elaborate hierarchy, councils, and palace intrigue.",
    ],
    # === THEME TROPES ===
    "war": [
        "Large-scale war and epic battles are central to the plot.",
        "The war backdrop raises the stakes, with armies clashing and kingdoms falling.",
        "Battle scenes and military strategy dominate this fantasy war story.",
        "Fighting on the front lines, war changes everything for these characters.",
    ],
    "political-intrigue": [
        "Political scheming, alliances, and backstabbing drive the plot.",
        "The political intrigue was masterfully done, every character has hidden motives.",
        "Court politics and power plays where one wrong move means death.",
        "Diplomatic negotiations, secret alliances, and political machinations at every turn.",
    ],
    "chosen-one": [
        "The protagonist is the chosen one, destined to save the world with unique powers.",
        "A prophecy foretells the hero's role, the weight of being the chosen one.",
        "She discovers she's the one foretold, the only one who can defeat the darkness.",
    ],
    "revenge": [
        "Revenge drives the plot, the protagonist seeks vengeance against those who wronged them.",
        "A revenge quest fuels the story, the heroine will stop at nothing to destroy her enemies.",
        "The thirst for vengeance consumes the character, revenge is the primary motivator.",
    ],
    "training": [
        "Training montages and power growth, the character becomes stronger through practice.",
        "The protagonist trains relentlessly, honing combat skills and magical abilities.",
        "The journey from weak to powerful through grueling training was satisfying to read.",
        "Leveling up through dedicated training, each new skill earned through sweat and blood.",
    ],
    # === CONTENT INDICATOR ===
    "spicy": [
        "The spice level is high, very steamy and explicit romance scenes.",
        "Incredibly spicy with detailed intimate scenes, this book is hot.",
        "The smut in this book was well-written and plentiful, very steamy romance.",
        "Explicit love scenes that steam up the pages, definitely not a fade-to-black.",
        "The sexual tension pays off with graphic, passionate scenes throughout.",
    ],
}
