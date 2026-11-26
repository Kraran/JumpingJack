# Gyrosphère — aperçu de rotation

Design retenu : proposition 2 de la planche de concepts, chrome segmenté, bande et optique cyan.

Asset : `assets/gyrosphere-preview-v1.png`, 24 vues dessinées avec imagegen intégré. Une passe supplémentaire a rendu le fond transparent. Le PNG final est conservé sans retouche.

L’aperçu isole chaque sphère entière, stabilise son diamètre et prépare 120 images interpolées avec raccord cyclique. La phase change selon le déplacement horizontal et s’inverse au retour. Présentation à 60 images/s avec gros plan et taille de jeu de 44 pixels natifs, soit +10 % sur la cible initiale de 40 pixels. Une légère sustentation accompagne le mouvement, sans réacteur ni jet.

La planche est désormais intégrée au jeu dans `gyrosphere-rotation-v1.png` : un atlas de 120 images de 44 pixels, préparé hors de la boucle de jeu. Le chargement du jeu ne nécessite pas numpy. L’aperçu initial reste indépendant de la simulation ; la vérification réelle se lance avec `python preview_gyrosphere_game.py`.

Régénérer : `python preview_gyrosphere.py` (dépendances de développement : numpy, imageio-ffmpeg).

## Prompt de dessin

Use case: stylized-concept. Asset type: a strict 6 COLUMN by 4 ROW animation sprite sheet, 24 frames, landscape 1536x1024, TRUE transparent alpha background. Reference is the approved design board: use ONLY design 2 GYROSPHERE from the MIDDLE COLUMN, preserve its polished silver chrome interlocking spherical armor, cyan luminous recessed equatorial band, small embedded cyan camera lens and tiny paired cyan marks. No red/gold variants. Create a smooth clockwise ROTATION AROUND THE VIEWING AXIS (like a wheel rolling to the right), a complete 360 degree rotation in 24 equally spaced steps: row 1 frames at 0,15,30,45,60,75 degrees; row 2 at 90,105,120,135,150,165; row 3 at 180,195,210,225,240,255; row 4 at 270,285,300,315,330,345. Entire shell including cyan band and lens rotates as a rigid solid sphere. Its round silhouette stays precisely circular and SAME DIAMETER, SAME CENTER AND SCALE in every cell. Cyan diagonal band changes orientation with rotation; lens goes around the projected center with the shell. Crucial: metallic ILLUMINATION and environment reflections remain anchored in world space (bright white highlight upper left, warm Egyptian temple reflection below), don't simply rotate a photograph and its light source. Use the identical panel construction every frame, no redesign or morphing. Each sphere 200 pixels diameter, centered in an equal 256x256 cell with empty transparent gutters. Whole sphere visible, no outer orbiting ring, no other objects, no hover glow beneath, no ground/shadow. No headings, labels, numbers, text, grid, backdrop or checkerboard. Premium realistic game sprite art; accurate spherical volume, crisp chrome/cyan features readable at 44 pixels diameter.

## Passe de transparence

Remove ONLY the gray background from this exact 24-frame robot sphere sprite sheet. Export a genuine transparent PNG, alpha=0 everywhere outside the spherical robot silhouettes and in every gutter. Keep all 24 spheres unchanged, including chrome reflections, cyan band, black panels, lenses, rotation orientations, centers and sizes. No checkerboard, no gray or white fill, no shadows outside the silhouettes. Exactly preserve the existing 6 columns and 4 rows and the original image dimensions. Do not redesign any sphere or move any object.
