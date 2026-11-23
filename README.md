# Jumping Jack — Les sables d’Horus

Premier prototype jouable d’un jeu de plateforme horizontal, développé en Python / Pygame. Le déplacement s’inspire du grand saut et du contrôle aérien de Mighty Bomb Jack ; la caméra amortie et le défilement continu recherchent la souplesse de Hollow Knight. Ce prototype propose sa propre physique, sans prétendre reproduire exactement celle des références.

![Le héros dans le désert égyptien](output/hero-animation-game.png)

## Jouer

Double-cliquer sur **Lancer.bat**, puis appuyer sur **Entrée**. Le jeu démarre en **plein écran Full HD 1 920 × 1 080 sur l’écran principal**. F11 permet de revenir en fenêtre. Pour démarrer directement en fenêtre : `python main.py --windowed`.

Python 3.10 ou ultérieur et Pygame 2.6.1 sont nécessaires. Version vérifiée : Python 3.13 sur Windows. Depuis un terminal :

```powershell
git clone https://github.com/Kraran/JumpingJack.git
cd JumpingJack
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Si Python et les dépendances sont déjà installés, `python main.py` ou **Lancer.bat** suffisent. Le lanceur utilise automatiquement l’environnement `.venv` s’il existe. Pour les scripts de prévisualisation vidéo, installer aussi les dépendances optionnelles avec `python -m pip install -r requirements-dev.txt`.

| Touche | Action |
| --- | --- |
| Flèches gauche / droite, Q / D ou A / D | Courir ; diriger le héros en l’air |
| Espace, flèche haut, Z ou W | Grand saut depuis le sol |
| Appuyer de nouveau en l’air | Couper l’élan vertical / freiner la chute |
| Maintenir le saut en descente | Planer lentement |
| Échap | Pause / reprise ; quitter depuis l’accueil |
| R | Recommencer le niveau |
| F11 | Plein écran / fenêtre |
| F3 | FPS, cadence P95, écran, VSync et rapports des trois plans |
| M | Activer / couper les effets sonores |

Le héros peut traverser les petites plateformes par dessous et se poser dessus. Maintenir Espace ne déclenche pas de sauts automatiques à l’atterrissage.

## Premier niveau

Un parcours de 9 600 unités dans un désert égyptien, avec pyramides, sphinx et temple. Ramasser les **52 reliques**, éviter les scarabées volants et les crocodiles du Nil, puis atteindre le sanctuaire à droite. Les reliques sont facultatives pour terminer : l’écran final indique le bilan, le temps et les morts.

Trois obélisques servent de points de reprise lorsqu’on les approche au sol. Une chute ou un contact avec un ennemi renvoie au dernier point activé, en conservant les reliques collectées. Une brève protection suit la réapparition. Les reprises ne sont conservées que pendant la partie en cours.

## Animation du héros

Le héros utilise **58 poses actives**, avec leur miroir pour la direction opposée :

| Mouvement | Poses |
| --- | --- |
| Course | 24, contre 4 auparavant |
| Repos / respiration | 4 |
| Retournement au sol | 8 |
| Retournement en l’air | 8 |
| Montée du saut / arrivée au sommet | 4 |
| Vol plané / mouvement de la cape | 8, contre une pose fixe auparavant |
| Chute | 1 |
| Réception | 1, brièvement avant la reprise de la course ou du repos |

La course avance selon la **distance réellement parcourue** : un cycle complet tous les 136 unités de niveau, soit 0,4 seconde à vitesse maximale. Ses 24 poses peuvent donc se succéder à 60 poses par seconde à pleine vitesse. La phase de l’animation est interpolée entre les mêmes pas de simulation que la position du héros ; ralentir ralentit aussi la cadence des jambes. Le vol plané possède une boucle indépendante de huit poses à 16 poses par seconde. Le repos utilise une respiration lente en aller-retour.

Toutes les cellules gardent une échelle commune et un ancrage explicite du corps, également respecté après inversion gauche/droite. Les poses sont préparées et préchargées en textures GPU avant de jouer. Il n’y a ni calcul d’image intermédiaire ni chargement de sprite dans la boucle d’affichage. La réception n’empêche pas de sauter immédiatement et la pause fige le cycle. Recommencer ou réapparaître remet l’animation à zéro.

Le héros dispose aussi d’un demi-tour rapide d’environ **0,16 seconde**, avec des poses dédiées au sol et en l’air. Une nouvelle inversion de commande fait repartir la rotation en sens inverse, sans saut d’image. Les déplacements, le saut et le vol plané restent immédiatement disponibles. La phase de course continue pendant le pivot, puis reprend à la pose correspondant à la distance parcourue. L’aperçu est `output/hero-turn-demo.mp4` ; le contrôle natif des 16 nouvelles poses et de leur cache GPU est enregistré dans `output/hero-turn-validation.json`.

Un aperçu avant/après à 60 FPS est disponible dans `output/hero-course-compare.mp4`. Le script développeur `python preview_hero.py` permet de le régénérer ; il utilise le paquet optionnel `imageio-ffmpeg`, qui n’est pas nécessaire pour jouer.

Vérification native de la course animée : `python verify_display.py --fullscreen-only --frames 360 --output output/hero-animation-gpu-timing.json`. Sur l’écran principal à 60 Hz : **59,97 FPS, P95 17,92 ms, maximum 18,55 ms et aucun intervalle supérieur à 25 ms sur 360 mesures**, dans la version à 42 poses, toutes présentes et toujours en cache GPU. La préparation CPU médiane était de 1,77 ms ; les dix bascules plein écran ont aussi réussi. Ces chiffres décrivent cet essai, pas une garantie pour toute charge système.

## Crocodile du Nil

Premier ennemi terrestre, dessiné d’après l’illustration fournie : longue queue recourbée, écailles cuirassées et silhouette basse. Il dispose de **16 poses de marche, 8 poses d’attaque/récupération et 8 poses de retournement**, dans les deux directions, préchargées sur le GPU.

Le demi-tour dure environ **0,16 seconde** : le crocodile pivote sur place par une vue de face avant de repartir. Il se déclenche aux limites de patrouille, lorsqu’il doit revenir dans sa zone après une charge et avant de viser un héros situé derrière lui. Le sens de déplacement change à la fin du pivot ; la zone de contact suit le raccourcissement de la silhouette pendant la rotation. Si le héros s’éloigne ou saute hors de portée pendant le demi-tour, l’attaque est annulée. `output/crocodile-turn-demo.mp4` présente la rotation à vitesse normale puis au ralenti ×4.

Le contrôle natif du retournement est enregistré dans `output/crocodile-turn-validation.json` : les huit poses dans chacun des deux sens ont été observées, avec toutes les textures de rotation encore en cache GPU. La cadence de cet essai était variable (47,96 FPS, P95 34,15 ms) ; le résultat de cadence ci-dessous décrit l’essai antérieur de marche/attaque.

Une comparaison contrôlée dans la même fenêtre (`output/crocodile-turn-comparison.json`) a ensuite mesuré 59,70 FPS avec un miroir instantané et 59,13 FPS avec le retournement animé ; le P95 passe de 17,38 à 17,53 ms et la préparation CPU médiane reste autour de 1,3 ms. Les mesures dépendent de la présentation de l’environnement de test.

Trois crocodiles gardent des portions de sol continues. Le premier se trouve avant la première fosse. Ils patrouillent lentement, se tournent vers le héros lorsqu’il s’approche près du sol, se ramassent brièvement et ouvrent la gueule avant une charge fulgurante. La direction de la charge est engagée au départ ; le crocodile ne suit pas le héros en plein mouvement. Il s’arrête avant les fosses et récupère avant de repartir.

| Paramètre | Valeur dans les unités du niveau |
| --- | --- |
| Marche | 28 unités/s |
| Détection | 250 unités du centre du corps, près du sol |
| Préparation de l’attaque | 0,12 s |
| Charge | 1 050 unités/s pendant au plus 0,24 s |
| Récupération | 0,85 s |

Un contact avec le corps ou la charge est mortel et renvoie au dernier point de reprise. La protection temporaire de réapparition reste valable. Sauter assez haut et planer permet de le dépasser. Les collisions sont vérifiées sur le trajet relatif complet du joueur et du crocodile, même si une charge passe entre deux positions affichées. Les crocodiles reviennent à leur position initiale après la mort du héros.

`output/crocodile-demo.mp4` montre une approche mortelle suivie d’un passage réussi par saut et vol plané. Pour la régénérer : `python preview_crocodile.py` (encodeur développeur optionnel `imageio-ffmpeg`). La vérification en plein écran se lance avec `python preview_crocodile.py --native-check` ; les données sont enregistrées dans `output/crocodile-gpu-timing.json`. L’essai sur l’écran principal à 60 Hz a mesuré **59,98 FPS, un P95 de 17,00 ms et aucun intervalle supérieur à 25 ms sur 359 mesures**, avec toutes les textures du crocodile présentes en cache. Les deux scénarios de collision ont également réussi dans cette vérification GPU.

## Fluidité

La simulation fonctionne à **120 Hz**, indépendamment de la fréquence d’affichage. Le rendu interpole les positions du personnage et de la caméra entre les pas de simulation. La caméra anticipe la course, ralentit progressivement et reste à l’intérieur du niveau.

**Trois véritables images indépendantes** composent l’arrière-plan :

| Plan | Contenu | Déplacement par rapport à la caméra |
| --- | --- | --- |
| Lointain | Ciel, pyramides et horizon | 0,08 × |
| Intermédiaire | Sphinx et temple | 0,24 × |
| Proche | Ruines et palmiers | 0,48 × |

Les trois positions proviennent de la même caméra interpolée, au même instant de rendu. Chaque position absolue est arrondie une seule fois au **pixel Full HD** le plus proche : aucune accumulation de petits déplacements susceptible de perdre des fractions de pixel. Les deux plans transparents se répètent sur une largeur entière, sans trou aux raccords. Le terrain jouable utilise sa propre caméra arrondie une seule fois, commune à tous ses objets fixes. Les unités de physique et les proportions du niveau sont conservées ; la projection vers les pixels Full HD se fait directement pour chaque objet.

La boucle utilise une horloge monotone haute précision. **Aucune limite de 240 FPS ne s’ajoute à la VSync.** Sous Windows, le jeu privilégie Direct3D 11, puis le choix automatique SDL, puis l’affichage logiciel si nécessaire. Il demande la VSync et vérifie le drapeau de présentation synchronisée du moteur SDL actif. La fréquence est lue sur le moniteur contenant la fenêtre ; elle est relue lors des déplacements et des bascules plein écran. Sans VSync disponible, une temporisation par échéances absolues suit la fréquence détectée, ou 60 Hz si elle est inconnue, sans rafales de rattrapage après un retard.

**Rendu GPU natif 1 920 × 1 080** : les trois plans, le terrain, les sprites, les formes et les textes sont composés dans une texture cible Full HD sur le GPU. Les textures sont chargées en mémoire graphique et réutilisées. Les formes courbes sont rasterisées une fois puis mises en cache ; les rectangles sont dessinés directement par le moteur. Le jeu ne redessine pas une image 720p sur le CPU pour l’agrandir, et ne transfère pas une image complète du CPU au GPU à chaque rafraîchissement. La présentation effectue une copie GPU de la cible Full HD vers l’écran, puis un seul échange synchronisé. La lecture des pixels vers le CPU est réservée aux captures explicitement demandées. Un rendu CPU Full HD reste disponible si le moteur accéléré ne peut pas être créé.

**Pixel-perfect** : les coordonnées et rectangles de destination sont entiers dans la cible Full HD. Les textes sont rasterisés à la taille Full HD et les poses du héros sont préparées à cette définition à partir de l’atlas original. Sur un écran 1 920 × 1 080, la présentation est exactement **1:1**, sans les anciennes bandes internes du rendu 720p. Sur un écran 3 840 × 2 160, elle est agrandie exactement **×2 par le GPU**, au plus proche. Sur les formats non multiples, l’image reste centrée avec des bandes pour conserver les pixels et les proportions. La taille minimale de fenêtre est 1 920 × 1 080 lorsque SDL permet de la fixer ; une sortie plus petite peut rogner l’image.

F3 indique les FPS mesurés, le 95e percentile des intervalles entre présentations, la fréquence détectée, le moteur, l’état déclaré par SDL de la VSync, la composition GPU ou le repli CPU, ainsi que le nombre de textures en cache. Ce drapeau confirme l’acceptation de la demande par SDL ; il ne mesure pas physiquement le balayage de l’écran. Une cadence parfaite sans aucune image retardée ne peut pas être garantie face à une surcharge, au pilote ou au compositeur Windows, notamment en fenêtre ou sur un autre moniteur. Les pixels des plans lents se déplacent naturellement moins souvent que ceux des plans proches. La perte de focus met automatiquement la partie en pause.

F11 conserve le moteur de rendu existant pendant la bascule. Si le pilote refuse cette opération, le jeu recrée proprement l’affichage et peut utiliser un mode logiciel de secours. Si aucun mode plein écran n’est accepté, il revient en fenêtre.

Le panorama et les textures sont préchargés avant la partie. Les textures sont également utilisées une fois dans la cible GPU hors écran pour préparer leur première apparition, sans présentation parasite ni lecture de pixels vers le CPU. Les sons sont synthétisés localement, sans téléchargement. Il n’y a aucune dépendance réseau pendant le jeu.

## Vérification

`python -m unittest discover -s tests -v`

Les 70 tests couvrent la physique, la collecte, les ennemis, les reprises, la victoire, le plein écran et ses replis, les rapports de parallaxe, l’absence de dérive et de trous de raccord, l’interpolation commune, les coordonnées Full HD, la transparence des plans, l’agrandissement entier et la cadence à 60/75/120/144/165/240/360 Hz sans double limiteur. Ils vérifient aussi la réutilisation et le préchauffage hors écran des textures, l’absence de transfert d’image complète ou de lecture GPU dans la boucle de composition, le cycle complet de 24 poses à 60 Hz, la phase indépendante de la cadence de simulation, les transitions aériennes et les ancrages des sprites. Pour les crocodiles : patrouille, déclenchement, charge engagée, limites de sol, récupération, collision continue, saut, protection de réapparition, placements, retournement stationnaire, abandon d’une attaque devenue hors de portée, contact pendant la rotation et 32 poses graphiques.

`python verify_display.py` ouvre une vraie fenêtre, mesure le défilement en fenêtre, en plein écran et après retour en fenêtre, puis vérifie dix bascules. Échap permet d’interrompre la vérification. Les mesures sont enregistrées dans `output/fullhd-gpu-timing.json`. Le test rapporte aussi les images dont l’intervalle dépasse 1,5 fois la période de l’écran ; il ne masque pas les retards de présentation.

Un essai distinct du démarrage plein écran sur l’écran principal à 60 Hz, avec F3 activé, est enregistré dans `output/fullhd-fullscreen-timing.json` : **59,97 FPS, médiane 16,71 ms, P95 17,72 ms et aucune image au-delà de 25 ms sur 359 intervalles mesurés**. La préparation CPU médiane est de 2,67 ms. Ces chiffres décrivent cette séquence, et ne garantissent pas la même cadence pour tous les moniteurs ou toutes les charges système. La recréation du moteur GPU et le repli après refus du moteur accéléré ont aussi été vérifiés dans une vraie fenêtre.

Pour une capture sans fenêtre : `python main.py --headless --play --frames 10 --screenshot capture.png`.

## Assets et références

Les vidéos et illustrations de référence fournies restent locales et ne sont pas distribuées dans le dépôt. Elles ne sont pas nécessaires au lancement. Les images du jeu et leurs sources générées sont enregistrées dans `assets/`. Les prompts et leur provenance figurent dans [assets/PROMPTS.md](assets/PROMPTS.md), [assets/PARALLAX-PROMPTS.md](assets/PARALLAX-PROMPTS.md), [assets/HERO-ANIMATION-PROMPTS.md](assets/HERO-ANIMATION-PROMPTS.md), [assets/CROCODILE-PROMPTS.md](assets/CROCODILE-PROMPTS.md) et [assets/HERO-TURN-PROMPTS.md](assets/HERO-TURN-PROMPTS.md).

Références techniques : [Pygame — affichage et VSync](https://www.pygame.org/docs/ref/display.html), [Pygame 2.6.1 — textures et cibles du moteur SDL2](https://github.com/pygame/pygame/blob/2.6.1/src_c/cython/pygame/_sdl2/video.pyx), [SDL — indicateurs du moteur de rendu](https://wiki.libsdl.org/SDL2/SDL_RendererFlags), [SDL — fréquence du moniteur](https://wiki.libsdl.org/SDL2/SDL_GetCurrentDisplayMode).

Les scarabées utilisent encore des animations de prototype. Le parcours sert de base pour régler ensemble le ressenti des sauts, la vitesse et la caméra avant de développer d’autres niveaux.
