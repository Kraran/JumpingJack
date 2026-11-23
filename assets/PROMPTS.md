# Images du prototype

Images créées avec l’outil intégré **image_gen**, sans appel à une API par script. Les fichiers consommés par le jeu sont tous copiés dans ce dossier.

## egypt-panorama.png

Prompt :

> Use case: game background asset. Create a cinematic photorealistic wide panoramic Egyptian desert environment for a side scrolling platform game, 3:1 landscape composition. Majestic ancient pyramids left and middle in the hazy distance, a realistic monumental sphinx toward center right, ruined sandstone temple colonnades at far right. Warm late afternoon golden sunlight, pale turquoise blue sky occupying upper 45%, atmospheric dusty depth, distant sand dunes, exquisitely weathered limestone and sandstone. Flat side-on horizon suitable for 2D parallax backdrop. Empty foreground sand at bottom 15%. Beautiful realistic materials, archaeological grandeur, restrained natural colors. NO people, NO hero, NO UI, NO lettering, NO borders. Save image as project game background.

## sandstone.png

Prompt :

> Use case: game texture asset. A square seamless tileable realistic weathered ancient Egyptian sandstone masonry wall texture. Straight orthographic front view, absolutely no perspective. Large finely detailed uneven beige-golden limestone blocks, horizontal courses and staggered vertical narrow mortar joints, worn chipped edges, subtle age cracks, natural grain. Blocks approx 4 across and 5 rows in the whole image. Sunlit warm beige stone, physically realistic archaeological materials. Soft even illumination, no cast shadows, no scenery, no people, no hieroglyphs, no text, no border. Entire image filled edge to edge with stone masonry.

## hero-atlas.png (création) et hero-atlas-v2.png (version utilisée)

Prompt de création (transparence demandée) :

> Asset type: production sprite sheet for a 2D side-scrolling platform video game. Transparent background. Exactly EIGHT full-body sprites of the SAME ORIGINAL adult male superhero, laid out in a strict evenly spaced 4 COLUMN by 2 ROW GRID. Each cell is square; each character fits inside its own cell with clear transparent margin; feet at same baseline within each cell; same character height and same scale throughout. Every sprite faces RIGHT in side view. Character: athletic elegant superhero with a short flowing crimson cape, fitted deep teal suit, gold boots and wrist bracers, golden falcon-themed half mask and chest emblem, dark hair. High quality hand-painted semi-realistic game character, clear silhouette, refined painterly material details, dramatic golden rim lighting, not pixel art, not chibi. Row 1: four successive running cycle poses, alternating legs and arms with cape following. Row 2 left to right: idle standing pose; upward jump knees bent; floating in air with arms spread wide cape fanning; falling feet downward. No lettering, no grid lines, no shadows on floor, no ground, no scenery. Exactly eight separate sprites, 4x2 regular grid.

Prompt de correction de transparence :

> Edit target: this exact 4x2 superhero sprite sheet. Remove the entire light white background completely. Output must be real transparent alpha with alpha=0 everywhere outside the eight superhero silhouettes, including between limbs and between sprites. No white pixels or semitransparent white wash left behind. Preserve all eight poses, their exact positions, original sheet dimensions and all character colors and details. Characters fully opaque; clean alpha cutout edges. Do not change composition or scale. This is a production game sprite atlas requiring genuine full transparency, not a checkerboard or white background.

Les poses sont chargées dans des cellules de grille et redimensionnées une seule fois au lancement. Le héros dispose aussi d’un dessin de secours si l’atlas est absent ou si sa transparence n’est pas exploitable.
