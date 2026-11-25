# Plasma solaire — proposition 2

Le rendu reprend l’animation validée dans `output/solar-plasma-option2.mp4` : filaments continus advectés vers l’avant, canal chaud ondulant, étincelles, éclat des mains, allumage et extinction progressive. Il s’agit d’un effet calculé par code, sans nouvelle génération d’illustration.

## Ressources utilisées en jeu

- `solar-plasma-color-v2.png` : atlas RGBA actif qui conserve les couleurs sur les fonds clairs ; 76 images, chacune de 1 330 × 84 pixels natifs, rangées en trois colonnes dans un atlas de 3 990 × 2 184 pixels.
- `solar-plasma.png` : source RGB de reconstruction et ancien rendu additif conservé pour comparaison.
- `solar-plasma.json` : format, fréquence de 120 images/s et ancrage du départ du rayon.
- `plasma_fx.py` : chargement et sélection de l’image selon l’horloge interpolée du tir ; découpage à l’obstacle.
- `solar.py` : préparation, émission mortelle et halo final sans dégâts. Le halo reste à la dernière position du tir dans le niveau.

Les deux orientations complètes de l’atlas sont préparées avant de jouer, préchargées et préchauffées hors écran. Le moteur utilise le mélange alpha standard avec des couleurs non prémultipliées. L’opacité est issue de l’intensité maximale du plasma source ; les canaux vert et bleu sont légèrement réchauffés pour conserver un cœur crème et des filaments dorés. Le ciel bleu ne s’ajoute plus au rayon jusqu’à le rendre blanc. Le chargement de l’ancien atlas reste possible comme repli si la ressource RGBA manque. Les images ne sont ni générées ni transférées à chaque frame. Les atlas restent sous 4 096 pixels de côté. La portée, les dégâts, les commandes F/B, les délais et l’interdiction du tir en vol plané restent ceux du rayon solaire existant.

## Reconstruire l’effet

```powershell
python -m pip install -r requirements-dev.txt
python tools/build_solar_plasma.py
```

NumPy et Pillow servent uniquement à cette reconstruction et à la prévisualisation ; Pygame reste la seule dépendance du jeu. Le script conserve les équations et la graine de l’aperçu validé. Il rasterise les turbulences, halos et étincelles, puis prépare les images à leur taille native de rendu et leur version RGBA. Pour reconstruire uniquement les couleurs depuis la source existante : `python tools/build_solar_plasma.py --color-only`. Cette conversion se fait par blocs lors de la reconstruction, jamais pendant le chargement du jeu ni le rendu.

Pour voir le rendu intégré, avec élimination d’un crocodile, tir aérien et refus du tir en planant : `python preview_solar.py`, qui produit `output/solar-ray-demo.mp4`. La vérification native du cache des deux textures et des impacts est consignée dans `output/solar-plasma-integration.json`.

Une comparaison alternée dans la même fenêtre est enregistrée dans `output/solar-plasma-comparison.json`. Le premier passage mesure 59,40 FPS pour l’ancien rendu et 59,48 FPS pour le plasma, avec une préparation CPU médiane de 1,63 et 1,90 ms. Les passages suivants deviennent variables pour les deux rendus (48,94 FPS pour le plasma, puis 44,98 FPS pour l’ancien rendu) ; cet essai ne garantit donc pas une cadence constante dans l’environnement de vérification. Les deux textures du plasma sont restées préchargées et réutilisées pendant les tirs.

## Vérification des couleurs sur le ciel

`python preview_plasma_color.py --native-check` compare le même tir et la même scène avec l’ancien atlas additif puis le nouvel atlas transparent. Il produit `output/solar-color-demo.mp4`, `output/solar-color-comparison.png` et `output/solar-color-validation.json`. Le contrôle GPU mesure les pixels blancs et dorés dans le rayon, et vérifie les transferts de textures. Les tests logiciels couvrent un ciel bleu soutenu, un ciel clair et un fond sombre, ainsi que la transparence extérieure, les deux orientations, les 76 poses et l’extinction finale.
