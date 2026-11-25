# Niveau 03 — Le Temple

Deux assets créés avec l’outil intégré imagegen, puis copiés dans `assets/` sans modifier les originaux générés. La transparence du second est conservée. Les mises à l’échelle, variantes de profondeur et atlas de flammes sont préparés au chargement ; aucun asset n’est généré pendant le jeu.

## Panorama : `temple-interior-v1.png`

```text
Use case: historical-scene. Asset type: seamless horizontal panorama background for a realistic 2D side-scrolling Egyptian temple interior game. Very wide 3:1 image, ideally 3072x1024. Entirely indoors, ancient Egyptian hypostyle hall: deep rows of enormous sandstone columns with painted faded red ochre and turquoise capitals, weathered relief walls, distant statuary of Horus and seated pharaohs, high dark ceiling beams, warm shafts of sunlight entering through small clerestory openings, dusty amber volumetric rays, distant alcoves and a central distant sanctuary. Straight horizontal camera for a platform game, no vanishing floor slope, the bottom fifth is dark architectural foundation, playable platforms will be added separately. Huge lateral repeating hall with similar architectural rhythm and matching brightness and column structure on both left and right edges for horizontal tiling. No exterior desert, no sky, no water, no modern technology, no people, no writing labels, no UI, no frames. Cinematic realistic fine textured sandstone game art, legible dark teal shadows against honey gold highlights, detailed but restrained contrast to preserve foreground character readability. Opaque full image, no transparency.
```

## Accessoires : `temple-props-v1.png`

Au chargement, le brasero est isolé par sa composante connexe principale : deux fragments de la porte voisine débordent dans la marge gauche de sa case et doivent être exclus du découpage. La planche d’origine est conservée. Les flammes utilisent désormais le dessin réaliste dédié décrit dans [TEMPLE-FLAMES-V2-PROMPT.md](TEMPLE-FLAMES-V2-PROMPT.md), avec une boucle de 48 images et une collision mortelle sur leur partie chaude.

```text
Use case: stylized-concept. Asset type: transparent PNG prop atlas for a realistic side-scrolling ancient Egyptian temple interior. A clean two by two grid of four separated architectural props on truly transparent background. Top left: one tall complete massive ancient Egyptian sandstone column, lotus capital, chipped base, carved faded turquoise and red details, fully visible straight frontal stage view. Top right: tall isolated broken column and its uneven stone stump with cracks, no floating fragments. Bottom left: a monumental recessed Egyptian stone sanctuary doorway, complete lintel and jambs, dark empty opening, Horus winged solar disk relief above, frontal view, flat baseline, no steps. Bottom right: a realistic ancient bronze wall brazier with a shallow bowl on a stone bracket, glowing embers only and no flames; flame animation will be added in game. Each prop confined entirely to its own quadrant, with generous transparent padding between cells. Same scale-independent warm honey sandstone, realistic fine stone grain, weathered relief details, directional warm lighting from upper left, no floor, no background, no drop shadow cast outside props, no characters, no labels, no text, no UI. No cartoon and no pixel art.
```

## Niveau jouable

14 400 unités : salles à colonnes, galeries effondrées, puis sanctuaire. Trois plans de parallaxe, braseros animés sur une boucle de 48 poses, sol de grès texturé, plafond solide, fosses, 34 plateformes en cinq tailles et trois rangées de lames. Douze scarabées robotiques et cinq scorpions noirs Exécuteurs ([assets et prompts](SCORPION-EXECUTOR-PROMPTS.md)) ; pas de crocodiles ni de vautours à l’intérieur. Deux points de reprise à 4800 et 9600 ; un médaillon à 12960 / 185. Les 79 cristaux maintiennent l’usage du vol plané et du rayon solaire.

Le désert mène au temple en conservant vies et médaillons. Le troisième médaillon peut donc accorder la vie supplémentaire. Sauvegardes et chargements prennent en charge le niveau 03. `LV03` à l’accueil ou `python main.py --level 3 --play --windowed` permettent de le tester directement.

Validation : `python tools/verify_level_layout.py --level 3` pour les 42 supports praticables (le plafond n’est pas un support d’atterrissage) ; `python preview_temple_level.py --native-check` pour les quatre vues et la vidéo, avec physique réelle et protection temporaire contre les ennemis.

L’ouverture du sanctuaire final contient désormais un escalier de pierre qui disparaît dans l’obscurité : [asset et prompt](TEMPLE-SANCTUARY-STAIRS-PROMPT.md). L’encadrement d’origine reste intact.

Sept vases cassables au rayon solaire complètent les obstacles : quatre au sol et trois sur des plateformes : [asset et prompt](EGYPTIAN-VASE-PROMPT.md).
