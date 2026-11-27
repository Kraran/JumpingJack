JUMPINGJACK — BEZELS

Trois atlas originaux générés avec imagegen à partir des concepts approuvés :
- egypt-v1.png : Les Portes d’Horus. Grès, colonnes de papyrus, Horus,
  disque solaire ailé, scarabées, reliefs et feuillage de palmier.
- greece-v1.png : Les Portes de l’Olympe. Marbre, colonnes doriques,
  méandres, lauriers, boucliers solaires de bronze et oliviers.
- solar-v1.png : L’Éclipse solaire (proposition C conservée). Pierre
  bleu-vert sombre, gravures solaires dorées et motifs de plumes discrets.

Sources visuelles : assets/concepts/bezel-egypt-v2.png,
assets/concepts/bezel-greece-v2.png, assets/concepts/bezel-proposals-v1.png.
Les concepts restent intacts. Les atlas de production ne contiennent ni
texte, ni zone de jeu fictive, ni interface.

Chaque atlas est partagé en deux moitiés égales : panneau gauche puis droit.
Le bord intérieur de chaque panneau se trouve au centre de l’atlas. Le moteur
utilise une mise à l’échelle proportionnelle de type cover, puis recadre la
source sur chaque marge. Le bord intérieur est conservé ; le surplus est coupé
vers l’extérieur. Les marges hautes et basses utilisent des bandes du même atlas.
Les décors restent fixes et ne recouvrent aucun pixel de la zone de jeu.

Rendu : trois textures GPU préchargées, sans lecture GPU pendant le jeu.
Le repli logiciel conserve un petit cache des recadrages par taille.
La définition et la mise à l’échelle entière existantes du jeu sont conservées.
Mode automatique : niveaux 1–4 égyptiens, niveaux 5–8 grecs.
Le choix global est indépendant des fichiers de sauvegarde de partie.

Contrôles : Configuration / Cadre d’écran. Entrée/A/clic pour choisir ;
Échap/B pour revenir. Gauche/droite permet aussi de parcourir les choix.
Le mode Automatique est la valeur par défaut des anciennes préférences.

Vérification native : python tools/verify_bezels.py
Rapport : output/bezel-validation.json
