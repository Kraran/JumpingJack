# Fragment de Rê — médaillon rare

Source active : `ra-medallion-v1.png`, RGBA transparent. Création avec l’outil intégré **image_gen**, à partir de la troisième proposition « Fragment de Rê » comme référence visuelle. Le faucon sculpté et le disque solaire brisé sont conservés.

## Prompt final

Use case: identity-preserve. Production transparent game collectible sprite: ONE ancient golden Egyptian medallion based strictly on PROPOSAL3 FRAGMENT DE RÊ in the supplied board. Only third design, not crystal or plasma sphere. Compact asymmetrical broken sun-disk medallion, raised falcon head profile looking right in lower half, top-left arc of engraved solar disc, top-right edge fractured into three sharp sun rays, small luminous amber faceted gemstone near upper center, intricate recessed decorative Egyptian glyphs and gold channels. Aged bronze-gold sculpture with polished sunlit edges, realistic painterly3D videogame material. Central bird relief MUST be clearly readable at small size, silhouette almost round with three protruding rays on right. Entire solid artifact visible, isolated centered, common warm upper-left lighting. NO exterior aura, particles, shine streaks, cast shadow, floor, scenery, labels, grid, text, HUD or extra objects: engine supplies animated light. True transparent alpha0 outside the medallion, no background wash. Generous20percent transparent margin on all sides. Square image1024x1024 or equivalent. Preserve identity of chosen third-design medallion closely.

## Animation et intégration

`medallion.py` prépare 48 poses en boucle sur 2,4 secondes : balancement de ±3°, pulsation dorée, halo et quatre scintillements orbitaux. L’objet solide mesure 80 pixels natifs, contre 40 pour les cristaux ; le HUD utilise une version réduite. Les poses sont regroupées dans un atlas préchargé sur le GPU, sans transformation ni transfert de texture pendant le jeu. Le flottement de ±2 unités et la phase suivent l’horloge de simulation et se figent en pause.

Un seul médaillon au niveau 1, en (6 540, 185). Ramassage avec la vraie collision du héros au sommet d’un saut depuis la plateforme (6 510, 455). Inventaire conservé après mort et redémarrage du niveau ; chaque niveau distinct n’accorde qu’un médaillon par partie. Au troisième, `redeem_extra_life` consomme les trois médaillons, accorde une vie supplémentaire et déclenche « VIE +1 OBTENUE » pendant trois secondes. Les niveaux récompensés restent mémorisés après cet échange. Une nouvelle partie réinitialise l’inventaire. Pas de sauvegarde sur disque ni de recharge d’énergie.

La mélodie synthétisée dure 0,76 seconde : do5, mi5, sol5, do6, avec attaque douce et décroissance. Elle est préchargée et respecte le réglage du son.

## Vérification et aperçu

`python -m unittest discover -s tests -p test_medallion.py -v`

`python preview_medallion.py --native-check`

Le second script produit `output/ra-medallion-demo.mp4` avec la même mélodie PCM synchronisée au ramassage, ainsi que `output/ra-medallion-jingle.wav` et le rapport GPU `output/ra-medallion-validation.json`. La démonstration protège le héros des ennemis pour isoler le saut et le ramassage ; la physique et les collisions des plateformes sont celles du jeu.
