# Musique des menus

**JumpingJack – The Lone Flyer**, composée avec Suno et fournie par le propriétaire du projet.
Source locale : `JumpingJack - The Lone Flyer.m4a` à la racine du projet, conservée sans modification.
Le jeu utilise uniquement `menu-the-lone-flyer.ogg` ; aucun outil de conversion n'est nécessaire au lancement.

Adaptation : stéréo 48 kHz, Ogg Vorbis qualité 5, normalisation linéaire en deux passes à −20 LUFS
(mesure après encodage : −20,07 LUFS, crête vraie −8,01 dBTP), sans compression de la dynamique.
Un fondu croisé circulaire à puissance constante de 1,5 seconde superpose la fin et le début.
La boucle dure 100,1135 secondes contre 101,6135 secondes pour la source.
Son début est placé au début du raccord : le retour du fichier et la sortie du raccord sont continus.

Le flux est chargé une seule fois et joué en boucle dans les menus, pause comprise.
Gain de référence : 65 %. La lecture commence dès le premier écran de chargement avec un fondu
de 1,2 seconde assuré par le mixeur SDL, même pendant les préparations bloquantes des assets.
Les reprises dans les menus s'ouvrent en 0,8 seconde et la sortie vers le jeu dure 2 secondes.
Le lancement du jeu suspend la musique après le fondu ; le retour aux menus reprend sa position.
Le menu pause et ses sous-menus appliquent un gain de 70 % du volume normal, sans modifier
le réglage enregistré ; le retour au menu principal rétablit progressivement le niveau normal.
Les réglages « Effets sonores » et « Musique des menus » offrent chacun un volume de 0 à 100 %,
par clic à l'endroit souhaité sur chaque jauge, ou par pas de 10 % avec les flèches gauche/droite
du clavier ou de la manette. Le clic permet un réglage au pourcent près.
Le clic maintenu permet aussi de glisser la jauge ; le volume suit immédiatement le pointeur,
reste limité entre 0 et 100 %, puis est enregistré au relâchement ou à la perte de focus.
Entrée/A coupe ou rétablit le son ; les volumes sont mémorisés séparément. Le raccourci M/RB conserve son rôle
de coupure des bruitages, sans modifier leur volume mémorisé. Les anciens fichiers de préférences
reçoivent par défaut un volume de 100 %, correspondant au niveau précédent.

Pour reconstruire l'asset avec les dépendances de développement :

```powershell
python tools/prepare_menu_music.py
```

Le rapport de préparation figure dans `output/menu-music-preparation.json`.
`python tools/verify_menu_music.py` vérifie la lecture native, la boucle, les transitions et le réglage
avec des préférences et sauvegardes temporaires.
