# Niveau 04 — La Tour, fin de l’Égypte

Asset : `tower-interior-v1.png`, créé avec imagegen intégré, sans clé API ni outil externe. Le décor reprend le grès, les frises peintes, les niches et les reliefs solaires du temple. La planche est conservée ; les raccords verticaux sont adoucis au chargement, puis les textures sont préchauffées sur le GPU.

## Prompt exact

```text
Production background tile for a realistic 2D side-view platform game set INSIDE a very tall ancient Egyptian temple tower. New vertical scrolling level, fixed horizontal camera width, ascends a huge stone shaft. Create one architectural backdrop module, full rectangular image, landscape3:2 around1536x1024. Straight-on orthographic elevation, no perspective floor or ground. Massive weathered warm sandstone interior wall with stacked shallow niches, faded turquoise and red carved bands, rows of small inset stone blocks and worn reliefs of falcons, solar disks and papyrus. Two distant dark vertical pilasters framing the edges, open readable middle suitable for gameplay platforms to be drawn separately, hints of deep dark recesses and faint amber dusty light from narrow unseen slits. Interior tower only: NO exterior sky, NO desert, NO water, NO staircases, NO platforms, NO people, NO torches, NO text or labels, NO big doorway/exit. Horizontal symmetry loosely balanced, restrained contrast, cinematic fine grained realistic stone textures matching an ancient Egyptian hypostyle temple. CRUCIAL seamless VERTICAL tiling: top edge and bottom edge must match the SAME courses of stone, same brightness and colors, no fade to black at either edge; architectural columns and relief rhythm continue naturally from bottom back into top. Full opaque image, no transparency.
```

## Géométrie et parcours

Largeur : 1280 unités de jeu, soit exactement la largeur de l’écran Full HD au facteur natif 1,5. Hauteur : 14 400 unités, comme la longueur du niveau 03. Le sol d’entrée se trouve à y = 14 300 et le palier du sommet à y = 261. La route compte 95 plateformes principales, le palier sommital et 21 plateformes secondaires à la même hauteur que certaines principales. Les écarts verticaux varient de 116 à 178 unités ; les décalages horizontaux sont souvent plus grands. La disposition utilise une graine fixe et reste identique entre les vies. Les plateformes restent solides par-dessous et sur les côtés ; Bas + saut permet toujours d’en descendre. Les murs ferment les deux côtés, sans déplacement horizontal de caméra.

Deux obélisques de reprise reposent sur les plateformes d’altitude intermédiaire. La tour contient 96 cristaux, avec 0, 1 ou 2 éclats par plateforme, onze scarabées, trois scorpions robots sur des plateformes de patrouille, neuf vases, sept flambeaux mortels et un médaillon de Rê près du haut. Quinze plateformes secondaires portent des lames. Les assets existants des ennemis, flammes, vases et lames sont réutilisés sans nouvelle génération. Le niveau 03 mène à cette ascension en conservant vies et médaillons. Le sommet termine l’étape égyptienne.

## Rendu et persistance

Trois plans verticaux : reliefs lointains à 0,18 de la caméra, piliers intermédiaires à 0,42, et murs/plateformes au premier plan à 1. La caméra est simulée à 120 Hz et interpolée avec le même alpha que le héros et les ennemis. Un seul décalage entier en pixels natifs s’applique à tous les objets du plan de jeu ; les positions de parallaxe sont calculées depuis la caméra absolue, sans accumulation de décalages. La synchronisation au rafraîchissement et le limiteur de secours existants sont conservés. Le rendu visible ne crée ni texture ni transformation d’image.

Sauvegarde : altitude du héros, caméra verticale, point de reprise, ennemis éliminés, cristaux et médaillon. Les sauvegardes horizontales antérieures reçoivent une caméra verticale nulle. Le HUD et les résumés de sauvegarde suivent la progression en hauteur. Les nouveaux textes sont traduits dans les vingt langues disponibles.

## Validation reproductible

- `python tools/verify_tower.py` : parcours des 96 paliers principaux avec la physique réelle, sans téléportation ni planage, en vérifiant les collisions mortelles des lames.
- `python tools/verify_tower_gameplay.py` : traversée complète avec ennemis et dangers actifs, énergie finie et aucune protection : victoire avec trois vies, zéro mort, 81 cristaux collectés et 14 tirs. Deux scorpions détruits, le troisième évité, onze scarabées détruits.
- `python -m unittest discover -s tests -p test_tower.py -v` : géométrie, collisions, caméra, cadences 60 à 360 Hz, reprises, médaillon, sauvegardes, transition de campagne et localisation.
- `python preview_tower.py --native-check` : passages sélectionnés à la base, à un point de reprise et au sommet, avec vrais sauts et protection temporaire contre les ennemis. La difficulté de l’ensemble des combats n’est pas évaluée par cette vidéo.
- `LV04` sur l’accueil ou `python main.py --level 4 --play --windowed` pour jouer directement.

Rapports : `output/tower-layout-validation.json` et `output/tower-render-validation.json`. Vidéo : `output/tower-level-demo.mp4`.
