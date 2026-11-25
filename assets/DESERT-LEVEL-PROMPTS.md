# Niveau 02 — Le désert

Création avec l’outil intégré **image_gen**, en mode génération. Sources actives enregistrées dans ce dossier ; elles sont chargées par `desert_art.py` et préparées sur le GPU avant la partie. Les images transparentes conservent leur alpha.

## desert-far-v1.png

Create production background art for a realistic side-scrolling Egyptian platform game, warm late-afternoon sun from upper left, no characters, no text, no HUD. Extremely wide landscape panorama 3:1. FAR BACKGROUND: open Sahara desert, vast amber dunes and distant eroded ochre ridges with tiny ancient Egyptian temple ruins almost buried in sand. Blue clear hazy sky occupies top 65 percent of image; low dune horizon at 65 percent height; distant sand layers only in lower third. No huge close objects, no giant statues, no sphinx, no palm forest, no pyramids. Calm photographic matte painting, physically plausible sandstone, fine wind ripples, believable atmospheric perspective. Entire image opaque, no transparency. Game-ready flat side-scroller backdrop with uncluttered upper sky and coherent horizontal horizon. Sharp premium game art, realistic, not cartoon.

## desert-middle-v1.png

Production transparent parallax layer for a realistic Egyptian desert side-scroller. Extremely wide panorama 3:1, true alpha transparency in upper 55 percent, no sky or painted background. A continuous low frieze of realistic warm amber sand dunes and partially buried ancient Egyptian sandstone temple ruins: broken column shafts, half-buried carved lintels, leaning small pylons eroded by wind, alternating with open low dunes. Everything is distant medium scale along the bottom 40 percent, continuous flat lower sand edge. Very low quiet dunes at both left and right edges at the same height for clean repeating edges. Warm sun upper left, soft photographic matte-painting materials, no black outlines, no characters, no modern objects, no labels, no border, no cast shadow outside silhouettes. Keep large transparent breathing space above the silhouettes. Perspective appropriate to a 2D horizontal side-view platform game.

## desert-near-v1.png

Production transparent NEAR parallax frieze for realistic Egyptian desert side-scrolling game. Wide landscape 3:1. Isolated band along the bottom third with weathered ochre sandstone outcrops, low wind-sculpted dunes, and a few large half-buried temple column bases and broken carved stones. True transparent alpha in top 55 percent; no sky, no distant scenery, no opaque background. Sharp sandy stone detail, realistic painterly matte-painting, sunlight from upper left, golden bronze palette. Keep all objects below middle height, no towering full columns. Left and right edges are low even sand at identical height so the band can repeat seamlessly. No characters, labels, text, grids or border. Low frieze only, authentic Egyptian archaeology buried by sand.

## desert-props-v1.png

Production transparent sprite atlas for realistic Egyptian side-scroller, FOUR separate isolated assets arranged on a precise equal 2x2 grid, generous clear transparent gutters, no labels or grid lines. All are directly side-on, warm golden sunlight upper-left, realistic detailed 3D game art, no floor, no background, no extraneous particles. TOP LEFT: a low ancient wooden footbridge deck, perfectly horizontal rectangular planked walkway with rough wood posts BELOW the deck and rope lashings, width four times height, NO rails or tall poles above deck, unobstructed flat upper surface, useful as solid horizontal platform. TOP RIGHT: wide massive ochre sandstone boulder, squat irregular rectangular wall silhouette with approximately flat upper ledge, weathered faceted rock, base flat, solid dense mass, no holes or arch. BOTTOM LEFT: dense clump of green Nile reeds, papyrus and bulrushes with a few brown seed heads, clear roots at flat bottom, realistic individual leaves. BOTTOM RIGHT: tall massive ochre sandstone boulder, irregular rectangular wall shape with a slightly flat top, broader base, dense solid weathered rocky mass with fine cracks, no arch or holes. Each asset completely contained in its cell with at least 12 percent transparent padding. True transparent alpha0 outside assets, no shadows on a floor. Square 2x2 atlas.

## desert-water-v1.png

Production photorealistic seamless texture for the surface of the Nile in a realistic side-view Egyptian platform game. Wide horizontal 2:1 rectangle entirely filled with WATER, no horizon, no sky, no land, no banks, no plants, no animals, no text, no border, no transparency. Blue-green and soft turquoise water with small fine horizontal ripples, physically plausible cool sky reflections and a few warm golden late-afternoon highlights from upper left. Calm broad river, rich subtle natural water detail, no foam, no surf, no dramatic waves. Texture must repeat cleanly at left and right edges. View water at shallow angle but without strong vanishing point or distant shore, uniform fine ripple scale across image. Suitable as subtle albedo under a game-engine animated ripple layer, realistic photography rather than vector illustration.

## desert-sand-v1.png

A production game texture: evenly lit golden ochre desert sand, orthographic flat albedo scan, no perspective, no horizon, no sky, no objects, no rocks, no footprints, no dunes or large sculpted shapes, no labels. Entire wide horizontal 4:1 rectangle filled edge-to-edge with natural sandy sediment. Subtle tiny sand grains and extremely fine soft wind striations, warm medium ochre-gold rather than bright orange, very LOW contrast uniform illumination, realistic material. Seamlessly tileable horizontally, left and right edges identical in tone and grain scale. Intended for the visible vertical soil face below the walkable ground in a side-view Egyptian videogame, so keep texture direction almost horizontal and uniform across the strip. No dark corners or vignette, no shadows, no borders. Opaque bitmap texture.

La texture du sol est préparée en une bande de 1 536 × 210 pixels natifs, répétée avec une origine commune dans le monde pour garder les raccords alignés entre portions de sol et bases des rochers.

## Intégration et animation

Les trois plans utilisent les rapports 0,08 / 0,24 / 0,48 et la même caméra interpolée que le premier niveau. Le plan lointain mesure 4 080 × 1 080 pixels natifs pour couvrir la fin du niveau sans raccord ni trou ; les deux autres plans répètent des bandes de 3 240 × 1 080. Les cinq passerelles, les six rochers et les joncs sont regroupés dans un atlas. Les rochers sont solides du sommet jusqu’au sous-sol, et Bas + saut ne permet pas de les traverser. Les tabliers des passerelles conservent les collisions sur toutes leurs faces ; leurs poteaux sont décoratifs.

La texture du Nil est animée par 48 poses pré-calculées sur 2,4 secondes : faible distorsion horizontale des lignes d’eau et reflets doux. Aucune déformation d’image ni chargement n’est effectué pendant le rendu. L’eau devient mortelle dès que les pieds passent sous y = 640 entre x = 700 et x = 3 140, même pendant la protection de réapparition ou le vol plané.

La géométrie se trouve dans `desert_level.py` : longueur 14 400, 26 supports suspendus dont cinq passerelles, six rochers, 73 cristaux, trois crocodiles limités à la première zone, dix scarabées et six vautours. Deux pylônes aux positions x = 4 800 et 9 600. Un médaillon en (12 960, 185), accessible au sommet d’un saut depuis le support en (12 870, 455).

Le bilan du premier niveau propose de continuer vers le deuxième ; les vies et médaillons sont conservés. Le redémarrage courant reste dans le même niveau ; une nouvelle partie commence au niveau 1. Les ennemis tués restent éliminés entre les vies, dans les deux niveaux.

## Vérifications et aperçu

`python tools/verify_level_layout.py --level 2` : recherche de sauts avec la vraie physique, les collisions solides et le danger de la rivière, sans ennemis. Les 40 supports sont atteints depuis le départ ; ce contrôle ne garantit pas la difficulté humaine face aux ennemis.

`python -m unittest discover -s tests -p test_desert.py -v`

`python preview_desert.py --native-check` : extrait avec quatre plans de caméra contrôlés. Le héros est protégé des ennemis pour montrer le parcours, mais conserve la physique, le danger de l’eau et le vrai ramassage. La vidéo est `output/desert-level-demo.mp4` ; le rapport est `output/desert-render-validation.json`.

Pour essayer directement le niveau : `python main.py --level 2 --play`.

## Relief jouable irrégulier et accès LV02

Le profil non périodique de `terrain.py` sert à la collision et au rendu. Des courbes cubiques relient des points de hauteur et d’espacement irréguliers ; les plus grandes dunes culminent à y = 355, soit 265 unités au-dessus du sol initial. La marche suit directement la hauteur locale, dans les deux sens. Le terrain est préparé en morceaux natifs texturés et ombrés, préchargés sur le GPU. Les personnages ne marchent pas sur des rectangles en escalier. Le rayon est arrêté par la vraie crête ; les insectes et les vautours utilisent des volumes locaux pour éviter les dunes et masquer leur vision derrière les reliefs.

Les plateformes sont relevées ou retirées lorsqu’elles seraient enfouies ; les 73 cristaux sont conservés. Les deux pylônes suivent le relief, sur de courts paliers. Les rochers restent infranchissables en marchant et le médaillon conserve son saut au sommet depuis y = 455. Le contrôle géométrique atteint les 40 supports.

Taper `LV02` à l’accueil démarre une nouvelle partie directement au niveau 2. Le code est insensible à la casse, accepte le pavé numérique et ignore les touches de modification de casse. Il ne fonctionne pas dans les autres menus ni pendant une partie.

`python preview_dunes.py --native-check` génère `output/dunes-lv02-demo.mp4`, `output/dunes-walking.png` et `output/dunes-validation.json`. La démonstration utilise le vrai code de menu et la marche réelle, avec une protection contre les ennemis pour observer les pentes.

## Raccords naturels entre berges et eau

Le profil des deux rives descend progressivement jusqu’à y = 640 au contact du Nil. Le sable est assombri près du bord et sa partie immergée devient progressivement translucide vers l’eau, dont la texture se prolonge sous le talus. Les surfaces restent alignées avec la collision réelle. Les ridelettes au contact utilisent un atlas transparent de 48 poses par rive sur 2,4 secondes, calculé au chargement et préchargé sur le GPU. Aucun nouveau bitmap source n’est requis : les textures de sable et d’eau existantes sont réutilisées. La simulation et la pause commandent également ces reflets.

`python preview_shore.py --native-check` produit `output/shore-transition-demo.mp4`, des captures des deux rives et `output/shore-validation.json`. Les tests vérifient que les berges atteignent exactement la surface, que le sable immergé se fond progressivement et que le bord praticable ne devient pas mortel à cause de l’effet visuel.

## Joncs ancrés dans le sable

Chaque touffe possède une pose préparée pour sa position exacte. La base suit le profil du terrain sur toute sa largeur, les racines sont enfoncées de 24 pixels natifs et la partie enfouie est masquée au niveau précis de la surface. Deux touffes ont été recentrées sur la berge pour que leurs racines restent entièrement sur le sable. Ces variantes partagent l’atlas des décors ; aucune transformation n’est effectuée pendant le défilement. Le contrôle visuel GPU des deux rives conserve zéro transfert de texture pendant le rendu.
