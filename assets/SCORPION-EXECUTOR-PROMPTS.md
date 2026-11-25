# Scorpion noir robot — Exécuteur

Créé avec le générateur d’images intégré (imagegen), à partir de la proposition 3 approuvée. Aucun modèle externe ni clé API supplémentaire.

## Assets
- `scorpion-executor-walk-v2.png` : atlas actif de 24 poses, six colonnes et quatre lignes, fond transparent.
- `scorpion-executor-parts-v1.png` : maillon articulé, canon au repos, canon chargé et effet de bouche.
- `scorpion-executor-walk-v1.png` : première passe de huit poses, conservée comme référence de génération.

Les rotations, les deux orientations, les 49 images de retournement en volume et leurs raccords de marche et les 64 poses de destruction sont préparées au chargement dans un atlas GPU. Le pivot utilise désormais un dessin dédié avec appuis des pattes et vue frontale ([asset et prompt](SCORPION-TURN-V3-PROMPT.md)). La queue s’articule et le canon vise de 0 à 90 degrés devant le scorpion ; les projectiles rouges sont distincts du rayon solaire du héros.

## Prompts exacts

### Première marche, huit poses
```text
Reference image role: only the THIRD / BOTTOM scorpion design, labeled 3 — EXÉCUTEUR, is the exact visual identity to preserve. Ignore proposals 1 and 2. Entirely robotic black gunmetal scorpion, massive serrated angular powered pincers, heavy armor, red vents and red sensors, industrial pistons, realistic detailed metal, side view suited to a 2D side-scrolling game, not a toy or cartoon. Transparent background, no text, no labels, no ground, no shadow. Produce ONE sprite sheet with EXACTLY FOUR COLUMNS and TWO ROWS, eight sequential walking frames. In each cell show the SAME complete robotic scorpion BODY with pincers and all eight mechanical legs, facing RIGHT in strict side profile with very slight depth showing the far legs. OMIT THE ENTIRE TAIL AND CANNON in every cell: they will be separately articulated by the engine. Leave a visible rear circular attachment socket. The front pincers are to the RIGHT, and are short powerful serrated black metal claws, not mammal heads. Consistent rigid body, perspective, scale, facing and armor detail across all 8 cells. Only the alternating four-pair leg gait and a subtle claw servo motion change smoothly through a looping walk cycle; frame 8 must lead naturally back to frame 1. Body center and floor baseline must be registered identically within all equal rectangular cells; each scorpion fits fully inside its cell with generous transparent gutters and none clipped. No tail segments, no stingers, no guns in this sheet. This is a production registered animation atlas, not a presentation with scattered poses.
```

### Pièces du canon et de la queue
```text
Reference image role: only the THIRD / BOTTOM scorpion design, labeled 3 — EXÉCUTEUR, is the exact visual identity to preserve. Ignore proposals 1 and 2. Entirely robotic black gunmetal scorpion, massive serrated angular powered pincers, heavy armor, red vents and red sensors, industrial pistons, realistic detailed metal, side view suited to a 2D side-scrolling game, not a toy or cartoon. Transparent background, no text, no labels, no ground, no shadow. Produce ONE production part sprite sheet with TWO COLUMNS and TWO ROWS, four separate parts on a genuinely transparent background. Top-left cell: ONE black metal segmented tail link module, elongated capsule with overlapping armored plates, tiny red conduit, circular rotary joint at each end, laid horizontally, strict profile, suitable to repeat into an articulated scorpion tail. Top-right cell: ONE short powerful laser cannon replacing the scorpion stinger, black gunmetal cylindrical barrel, red focusing lens and small heat sink vents; cannon laid horizontally with the muzzle pointing RIGHT, base pivot at the LEFT, strict side profile, no legs, no body, no organic sting or hook, no laser beam. Bottom-left cell: the SAME laser cannon during an energized firing state, red hot emitter lens, red lit vents, still pointing RIGHT, no beam crossing the cell. Bottom-right cell: a compact isolated red/white muzzle-flash bloom with a small red plasma projectile just ahead of it, horizontally oriented RIGHT, no cannon, no body. Keep all parts completely separated within their own equal cells, with large transparent padding. Preserve the Exécuteur industrial black metal and red palette. Highly detailed realistic sci-fi production cutouts.
```

### Intervalles, marche finale de 24 poses
```text
Edit/reference: this is the approved Exécuteur black robot scorpion BODY walking sheet (no tail, tail and laser cannon are separate rigged parts). Expand this walking motion into a NEW production animation atlas with EXACTLY SIX COLUMNS and FOUR ROWS, 24 numbered-in-time but UNLABELLED frames, ordered left to right then top to bottom. Preserve the same realistic black gunmetal armor, red reactor vents and sensors, powerful serrated pincers, strict right-facing profile, no tail or cannon. Create smoothly spaced genuine intermediate eight-legged walking poses between the reference poses, forming one complete seamless alternating leg gait cycle. Identical camera, rigid body size, alignment, body center and ground baseline in EVERY equal cell; only legs and tiny claw servos move. Every body completely visible with space around it, no clipping, no missing limbs, no extra creatures per cell, no text, no numbers, no shadows or ground, truly transparent background. Ideal canvas 2048x1365 or larger, each of 24 equal cells large enough to preserve metal detail. Do not return an 8-frame sheet, exactly 6 by 4 frames. Keep all panels consistent in body orientation, scale and baseline.
```

## Intégration et validation

Cinq ennemis uniquement dans le niveau 03, aux abscisses 1500, 6400, 8450, 10200 et 13660. Marche lente, détection devant lui avec obstacles, visée continue, charge de 0,72 seconde et bref verrouillage avant le tir, recul puis recharge. Les balles sont mortelles, arrêtées par les plateformes et les murs ; le héros peut éviter le tir horizontal en s’accroupissant. Le rayon solaire détruit le robot avec étincelles et fumée. Les ennemis détruits restent morts après une perte de vie et dans les sauvegardes. Les anciennes sauvegardes demeurent chargeables.

`python preview_scorpion.py --native-check` produit la vidéo, les captures et `output/scorpion-validation.json`. La galerie teste les six orientations avec cible protégée, puis une destruction dans la géométrie réelle du temple. Elle ne remplace pas un test de difficulté de tout le parcours.


## Ancrage de la queue

Le premier maillon est fixé sur la rotule arrière visible de la carapace, avec un point mesuré pour chacune des 24 poses de marche. La chaîne est dessinée derrière le corps ; la carapace recouvre sa racine. Les maillons se chevauchent pour éviter les jours, et les clips de pivot et de destruction réutilisent le même raccord. Les tests vérifient le raccord et la continuité de la chaîne pour 24 poses, deux orientations et trois phases de mouvement. Aperçu : `output/scorpion-tail-demo.mp4`.

## Explosion du robot

La mort réutilise `robot-beetle-explosion-v1.png`, sans nouvelle génération d’image : mêmes flammes et fumée que les scarabées, portées de 120 × 80 à 432 × 288 pixels natifs. Des fragments issus du scorpion (carapace, pattes, queue, canon) sont projetés avec rotation et gravité, avec vingt étincelles. La séquence de 1,25 seconde comporte 64 images précalculées, dont la dernière est complètement transparente. Le dessin ne crée ni texture ni rotation pendant le jeu.

`python preview_scorpion_explosion.py --native-check` filme une destruction réelle au rayon solaire dans le temple, à vitesse normale puis au ralenti, et produit `output/scorpion-explosion-validation.json`. Les tests couvrent la taille des flammes, la disparition finale, l’interpolation et l’absence de répétition.
