# Monde 2 — Direction visuelle et ressources grecques

## Ressources des niveaux de campagne

Les niveaux 05 à 08 utilisent les sauts, ennemis et récompenses existants. Le 05 mesure 12 000 unités ; les 06, 07 et 08 mesurent 14 400 unités. Le 08 monte par terrasses de 620 à 380 unités avec un accompagnement vertical amorti de la caméra ; il se termine devant le Parthénon. Les sols décoratifs restent intégrés à leurs bâtiments dans chaque plan de parallaxe.

Les panoramas opaques de campagne couvrent toute la course de caméra sans répétition ; les plans transparents répètent leurs décors et terrains ensemble. Les galeries ont leur propre plafond en pierre. Aucun transfert de texture n’est nécessaire pour changer de décor en cours de jeu : les variantes sont préchargées.

Le plafond visible du niveau 07 appartient au panorama des galeries et défile avec les murs (0,08). La géométrie de plafond reste utilisée pour les collisions ; aucune bande découpée supplémentaire n’est dessinée à la vitesse du sol, afin de conserver une architecture continue et les ouvertures de lumière d’origine.

Dans le niveau 07, les colonnes et portiques des plans intermédiaire et proche reposent sur des soubassements continus en marbre, préparés à partir de la maçonnerie du décor des galeries. Chaque soubassement recouvre légèrement le pied des structures et appartient à la même texture : il défile avec elles, y compris derrière les fosses du parcours jouable.

## Vérification de l’intégration

La suite complète a passé 563 tests après l’ajout des hoplites ; les derniers ajustements de sauvegarde sont couverts séparément par les tests ciblés des gardiens et des cases. `output/greece-layout-validation.json` confirme 156 supports accessibles et quatre médaillons atteignables sans planage ni énergie. Le contrôle de combat borné `output/greece-gameplay-validation.json` termine actuellement les niveaux 05, 06 et 08 avec ennemis actifs, trois vies initiales et énergie finie ; il échoue encore au niveau 07. Ce résultat limite la validation automatique de la difficulté des galeries et ne constitue pas une preuve d’impossibilité du parcours. Les vies et la protection de réapparition suivent les règles normales ; ces traversées sont indépendantes.

`output/greece-world-render-validation.json` confirme le moteur Direct3D 11 et zéro nouveau transfert de texture sur les 720 images des prises de vues grecques. La vidéo utilise des positions de départ choisies et une protection contre les ennemis ; elle illustre les décors et ne constitue pas la preuve des traversées complètes. Le compteur de textures résidentes reste borné à 3 072, avec 2 469 textures observées après les quatre prises. Ces contrôles ne mesurent pas le ressenti d’une manette physique.


### Galeries — greece-gallery-v1.png

Outil intégré image_gen. Transparence : non.

Use case: historical-scene. Asset type: opaque far parallax background for level 07 of JumpingJack, ancient Greek marble temple substructure galleries. Very wide 3:1 panorama in richly detailed realistic archaeological game art. Orthographic side-scroller elevation, horizontal floor baseline 88% down canvas. Vast cool shadowed halls of ivory and grey veined marble, Doric columns supporting heavy stone beams, cracked retaining walls, worn relief friezes, distant stone urns in niches. Three large broken ceiling skylights admit pale blue daylight and restrained warm shafts. Layered architecture gives depth, but no perspective road or central vanishing point. Soft contrast distant architecture for readable hero foreground. Muted slate blue / ivory / faded bronze palette. No Egyptian motifs, no living people, no enemies, no platforms floating in art, no text, no UI. No olive trees indoors, no sea in hall. Keep upper third in shadow for HUD legibility. Complete opaque scene to edges with plausible repeat at left/right.

### Colonnes des galeries — greece-gallery-props-v1.png

Outil intégré image_gen. Transparence : oui.

Use case: historical-scene. Asset type: transparent modular scenery sprite sheet for an ancient Greek marble gallery side-scroller. Wide landscape 3:1 canvas. Three separate objects, generous transparent margins and gaps: left one tall intact fluted Doric column with square capital and round stepped foot; center two broken fluted columns supporting a cracked horizontal stone lintel with a small Greek key frieze; right one large Greek terracotta amphora beside low fallen marble blocks. All objects fully visible, bases on common horizontal baseline near bottom 95%, tallest reaches 10% from top. Richly detailed realistic ivory veined marble with muted cool grey shadows and bronze patina accents, morning shafts of light from upper left, orthographic front elevation. NO background wall, no sky, no ground strip, no water, no people, no statues, no Egyptian motifs, no text, no UI. Actual transparent alpha=0 outside objects and in all openings. Production game cutout asset with clean silhouette.

### Acropole lointaine — greece-acropolis-v1.png

Outil intégré image_gen. Transparence : non.

Use case: historical-scene. Asset type: opaque far parallax landscape for the final ancient Greek level 08 of JumpingJack. Very wide 3:1 panorama, richly detailed realistic archaeological game art. Late afternoon golden sun from upper left. Open pale gold and azure sky top 60%, blue misty Greek mountains and distant Aegean sea low on horizon. A massive limestone Acropolis hill rises along the lower third, carrying a distant recognizable Parthenon with Doric columns and pediment at center-right, smaller sanctuaries and ancient city terraces below. Heroic grandeur, warm ivory / bronze / muted terracotta palette, soft atmospheric perspective to leave hero silhouette readable. Side-scroller backdrop viewed across the valley; no perspective road, no close columns, no foreground trees, no people, no text, no UI, no Egyptian motifs. Background landscape continues through bottom edge, no blank margins.

### Parthénon final — greece-parthenon-v1.png

Outil intégré image_gen. Transparence : oui.

Use case: historical-scene. Asset type: transparent final landmark for ancient Greek side-scrolling game JumpingJack. Wide landscape 3:1 canvas showing one grand Parthenon inspired Doric temple, front and long colonnade in a very shallow three-quarter view that remains suitable for side-scrolling elevation. Richly detailed weathered ivory marble, triangular sculpted pediment, many fluted Doric columns, faint red and blue frieze, bronze accents. Warm golden late-afternoon light upper left. Temple stands on three wide shallow marble steps with a perfectly horizontal bottom baseline. Deep dark interior visible BETWEEN columns with actual transparent openings where appropriate. Complete monument visible with transparent padding all around, no clipped pediment. No landscape, no sky, no soil strip, no trees, no statues, no characters, no text, no UI, no Egyptian motifs. True transparent alpha=0 background around isolated temple. The final route passes in front of these steps; this is background scenery only.


Direction retenue : **Les hauteurs d’Hélios**. Les niveaux 05 à 08 prolongent désormais la campagne égyptienne. La scène représentative reste disponible comme référence visuelle.

## Identité

Marbre ivoire, calcaire chaud, bronze patiné, mer turquoise et oliviers argentés. Architecture dorique, frontons triangulaires, traces de polychromie rouge et bleue. Le héros et les cristaux gardent leur apparence actuelle. La statue d’Athéna est un élément de décor, sans collision ni attaque.

Trois plans indépendants utilisent les rapports existants 0,08 / 0,24 / 0,48. Les plateformes reprennent les cinq largeurs 120, 180, 240, 300 et 360, avec 32 unités d’épaisseur. Les textures sont préparées avant le rendu.

## Progression proposée

| Niveau | Titre | Parcours et intention |
| --- | --- | --- |
| 05 | Les Rivages d’Hélios | Côte, terrasses et ruines ouvertes ; reprise plus accueillante après la tour, puis sauts et traversées au-dessus de l’eau. |
| 06 | La Voie des Statues | Voie processionnelle, colosses et portiques ; alternance d’aires ouvertes et de passages resserrés, détours aériens récompensés. |
| 07 | Les Galeries du Marbre | Soubassements fissurés et étages superposés ; tir accroupi, descente volontaire et changements de hauteur. |
| 08 | L’Acropole du Soleil | Ascension extérieure par terrasses, traversées panoramiques et arrivée au Parthénon au soleil doré. |

Le chemin obligatoire reste possible sans énergie solaire. Les comportements d’ennemis, les commandes, la physique, le score, les sauvegardes et les animations existantes servent de base. La transition 04 → 05 conserve la partie, et les cinq cases acceptent les huit niveaux en conservant les anciennes sauvegardes.

## Prévisualisation

`python preview_greece.py` exporte trois captures et un rapport. `python preview_greece.py --native-check --video` vérifie le rendu GPU et exporte aussi une vidéo Full HD à 60 images/s. Échap ou la fermeture de la fenêtre interrompt l’essai.

Le script fait avancer le héros avec la vraie physique à 120 Hz, la caméra amortie et l’interpolation existantes. Il ne crée pas de niveau de campagne : les niveaux 01 à 04 et main.py restent inchangés. Les préférences et cases de sauvegarde de l’essai utilisent un dossier temporaire. Le parcours de 4 800 unités comporte un sol continu, des plateformes et des cristaux ; il sert à juger les proportions et la lisibilité. Il ne valide pas encore les combats, la manette ou les sauvegardes du futur monde 2.

Livrables : `output/greece-study-coast.png`, `output/greece-study-athena.png`, `output/greece-study-acropolis.png`, `output/greece-study-demo.mp4` et `output/greece-study-validation.json`.

## Ressources et prompts

Création avec l’outil intégré **image_gen**, puis ajout d’un cinquième asset pour le sol. Les PNG originaux sont copiés dans assets ; leur transparence est conservée. Les changements d’échelle sont réalisés au chargement, comme les décors existants.

### Sol sec — greece-ground-v1.png

À la demande de l’utilisateur, l’eau au pied des ruines est recouverte de terre sèche avec des passages irrégulièrement pavés : dalles de calcaire usées, pierres manquantes, joints de terre et herbes sèches. La mer reste au loin ; son horizon est remonté dans la composition pour qu’elle demeure visible au-delà du terrain. Le terrain est réparti en deux parties : celui des temples est intégré à leur plan (0,24), celui de la statue, de l’olivier et des ruines proches à leur plan (0,48). Chaque sol est composé avec ses bâtiments dans la même texture au chargement, pour éviter tout glissement ou différence d’arrondi. La bande proche reste sous les socles des temples du plan intermédiaire. Le sol de collision et les plateformes gardent leurs dimensions.

Transparence : oui. Prompt de l’outil intégré image_gen :

Use case: historical-scene. Asset type: independent near-ground terrain strip for a richly detailed ancient Greek side-scrolling platformer, to cover water mistakenly showing underneath nearby temples. Very wide 3:1 landscape. Show a broad continuous DRY LAND apron of dusty warm ochre earth, compacted soil, scattered pale limestone pebbles and sparse dry grass, with an irregular ancient footpath running horizontally across it. The path is badly paved: discontinuous groups of worn uneven ivory limestone paving stones, missing slabs, cracked edges, soil filling wide joints, occasional stones half buried. Natural archaeological realism, clear morning sunlight from upper left, warm restrained beige and terracotta palette, subtle ground shadows. Side-scroller shallow oblique view, no perspective vanishing road, no raised wall or cliff, no sea, no water, no sky, no buildings, no columns, no trees, no characters, no text. Full width ground, seamless left/right texture feel. The upper 15% of the canvas is fully transparent alpha=0; an irregular softly broken soil silhouette starts around 20% from top, then terrain is fully opaque all the way through the bottom edge and the left/right edges. The upper transition must look like the distant edge of dry earth, no glow, no white border, no checkerboard. This terrain is a separate scenery plane behind the playable marble ledge; preserve realistic fine earth and worn stone detail.

### Fond lointain — greece-far-v1.png

Transparence : non.

Use case: historical-scene. Asset type: farthest parallax background for JumpingJack level 05, an ancient Greek coastal side-scrolling platform game. Generate a very wide 3:1 panoramic raster painting with realistic archaeological materials and cinematic game environment detail, bright clear morning light from upper left. Pale azure sky occupies top 55%, distant blue hazy mountains and Aegean islands along low horizon, turquoise sea in lower third, distant headland at right bearing a small clearly recognizable Doric Parthenon silhouette, tiny ivory ancient Greek coastal town below it. Atmospheric perspective, restrained ivory / turquoise / blue mist / pale gold palette. All architecture is FAR AWAY, soft and low contrast; preserve open sky for airborne hero readability. Sea continues to bottom edge. Orthographic side-scroller background, not a perspective road into distance. No foreground ground, no close columns, no close statues, no characters, no platforms, no text, no UI, no Egyptian motifs. Opaque image.

### Temples intermédiaires — greece-middle-v1.png

Transparence : oui.

Use case: historical-scene. Asset type: transparent middle parallax plane for an ancient Greek coastal side-scrolling platformer. Very wide 3:1 canvas. Realistic richly textured ivory marble archaeological game scenery, morning sun from upper left, muted cool shadows. Three separate architectural groups anchored at baseline 88% down canvas: left a low ruined Doric colonnade, center a modest six-column Doric temple with triangular pediment and faint red/blue painted frieze, right a cluster of broken columns and low stone terraces. Tops of tallest temple at 40% down canvas. Large empty spaces between groups allow a sea background to show through. Orthographic elevation side view, horizontal baseline, small amount of depth in column capitals, no perspective floor receding into distance. These buildings are scenery BEHIND the playable route. Background completely transparent alpha=0, including sky AND between columns. Top 35% and side margins fully transparent. Restrained contrast so hero is legible in front. Small ground bases only directly under objects, no full-width ground strip, no water, no sky, no mountains, no characters, no UI, no lettering, no Egyptian motifs, no platforms.

### Olivier et Athéna — greece-near-v1.png

Transparence : oui.

Use case: historical-scene. Asset type: transparent near background parallax plane for ancient Greek side-scrolling platform game JumpingJack. Very wide 3:1 composition, realistic detailed ivory marble and bronze patina, clear warm morning sun from upper left. Three widely spaced groups on one horizontal baseline near bottom: at left a mature olive tree with fine silver-green leaves beside fallen fluted column drums; at center-right a large full-body classical marble statue of Athena wearing helmet and robes, standing on a square plinth, shield resting at her side, intact readable silhouette; at far right sparse broken Doric pillars and olive shrubs. Statue is a landscape landmark behind gameplay, not an enemy. Objects rise from baseline 94% down canvas, tallest crown reaches 28% from top, statue top 36% from top. Keep generous open negative space between all groups for gameplay. Side elevation with subtle natural depth, realistic archaeological game art matching a richly rendered Egyptian platformer. Actual transparent alpha=0 background everywhere outside objects AND through foliage. No sky, no sea, no distant hills, no full-width ground, no characters, no text, no UI, no Egyptian imagery. Both side margins transparent, nothing clipped.

### Plateformes — greece-platforms-v1.png

Transparence : oui.

Use case: historical-scene. Asset type: production transparent sprite sheet for ancient Greek marble platforms in a side-scrolling game. Wide landscape canvas, exactly FIVE isolated horizontal stone platform slabs in FIVE equally spaced horizontal rows, centered in each row. Top to bottom relative widths 1/3, 1/2, 2/3, 5/6, full width (leave side padding). Each slab SAME HEIGHT, a long thin rectangular block, perfectly horizontal flat top and straight vertical sides, orthographic FRONT ELEVATION, only a very thin lit upper bevel, absolutely no deep visible top surface. Rich realistic carved ivory marble veining, restrained antique bronze corner caps, Greek key meander carved along front face, small central sun rosette. Archaeological game asset, precise crisp silhouette, morning light upper left, subtle shaded underside. No hanging ornaments, no vegetation, no legs or columns, no brackets extending beyond rectangle, no spike, no Egyptian motifs. Actual transparent alpha=0 background around and between every slab. Large transparent spacing so the five equal-height horizontal row cells can be extracted automatically. No text, no labels, no UI, no cast shadow outside object. These are five sprites, not scenery.
