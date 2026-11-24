# Correction des saccades de début de partie

Vérification du 24 novembre 2026, Windows, rendu direct3d11, Full HD, écran 60 Hz.

## Cause observée et correction

Les sprites étaient préchargés, mais le premier affichage jouable créait encore la police et le texte d’aide, les premiers compteurs de collecte, les ombres et certaines variantes de petites formes. Avant correction, la première image mesurée demandait 19.78 ms de préparation hors présentation. Les cinq premières secondes créaient 13 textures supplémentaires, quatre textes et neuf formes.

Le chargement prépare maintenant les scènes d’accueil, jeu et pause hors écran, toutes les valeurs du compteur d’éclats, les avertissements de jauge et les formes usuelles. Le travail GPU est soumis sans présentation ni lecture des pixels. La préparation est rejouée après recréation de l’affichage. Un ramasse-miettes complet termine le chargement ; le GC reste actif pendant la partie.

## Contrôle après correction

La mesure finale a été exécutée seule après les tests. Première image : 1.24 ms de préparation hors présentation. Les 300 premières images jouables (cinq secondes à 60 Hz dans ce script), puis les 300 images du même parcours recommencé, n’ont créé aucune texture, aucun texte et aucune forme. Le script comprend déplacement, collecte, saut, vol plané, accroupissement et tir. Il conserve les premières images dans le rapport, sans éliminer une période de chauffe du gameplay.

Première seconde : médiane de préparation 2.233 ms ; P95 4.118 ms. Intervalles de présentation : médiane 16.674 ms ; maximum 19.895 ms. Aucun intervalle supérieur à 25 ms sur cette mesure de 600 images.

252 tests réussis. Les régressions ajoutées vérifient l’absence de modification du monde, d’échange écran et de lecture GPU pendant la préparation, ainsi que l’absence de création de police, texte ou forme dans le scénario des cinq premières secondes.

Les temps hors présentation comprennent la soumission des commandes GPU ; ils ne sont pas un profil matériel GPU. Les variations de présentation liées à Windows, à la VSync et au pilote subsistent : ce contrôle retire la préparation tardive identifiée, sans garantir l’absence de toute image retardée dans d’autres conditions. Les trois images d’accueil du script précèdent le chronométrage du gameplay.

Reproduire : `python tools/profile_startup.py --output output/startup-profile.json`.

Rapports bruts : `output/startup-before.json`, `output/startup-after.json`.
