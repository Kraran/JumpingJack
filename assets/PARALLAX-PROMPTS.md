# Trois plans de parallaxe

Créés avec l’outil intégré **image_gen**. Chaque image est préchargée puis préparée une fois à 3240 × 1080 pour le rendu Full HD. Les plans middle et near ont une vraie couche alpha ; leur ciel reste transparent. Les prompts ci-dessous sont ceux de la création originale.

## parallax-far.png

Transparence demandée : non.

Game background layer 1 of 3, Egyptian platformer. A very wide 3:1 photorealistic panorama, pale blue and warm gold late-afternoon sky upper two thirds, distant hazy Egyptian pyramids and very distant desert mountains along lower third, sand horizon at 560 of 720 pixels. Atmospheric perspective and archaeological grandeur. This is ONLY the farthest background plane. No close architecture, no sphinx, no temples, no vegetation, no characters, no UI, no text. Fine realistic natural detail, warm restrained colors. Sky completely opaque. Landscape 3:1.

## parallax-middle.png

Transparence demandée : oui.

Production game transparent PNG background layer 2 of 3. Very wide landscape 3:1 canvas representing 2160x720 view, orthographic side view for Egyptian desert platformer, photorealistic weathered monumental Egyptian sphinx at left-center and ruined temple colonnades at right-center, distant middle-depth dunes at their base, warm late-afternoon golden light from left, atmospheric archaeological realism. Buildings rise from baseline near bottom at y=620, tops around y=270. Keep upper third COMPLETELY EMPTY AND TRANSPARENT. Keep 100px wide left and right margins COMPLETELY EMPTY AND TRANSPARENT; objects do not touch those margins. There is NO sky, NO background landscape, NO full-canvas sand rectangle, NO white or checkerboard backdrop. Individual architecture and little ground beneath them are fully opaque realistic cutout silhouettes, everything else actual alpha=0. Genuine transparent background is essential. No people, no lettering, no UI. Suitable for independently scrolling parallax game layer, the sky and pyramids are in a separate image.

## parallax-near.png

Transparence demandée : oui.

Production game transparent PNG background layer 3 of 3. Very wide landscape 3:1 canvas representing 2160x720 side view, photorealistic Egyptian desert ruins in the near background: sparse clusters of beautifully eroded sandstone fallen columns, low broken temple walls and a few desert palms. All objects stay in the bottom 45% of image. Tallest palm reaches y=330 of720 and ground baseline y=650. Warm afternoon light from upper left. Visually rich realistic detailed sandstone with warm beige tones, occasional dark green palms. Three separate spaced clusters with lots of empty space between. Keep upper 40% and both 100px side margins COMPLETELY TRANSPARENT alpha=0. No sky, no pyramids, no sphinx, no solid background, no white or checkerboard. Genuine full alpha transparency outside cutout objects, fully opaque objects, clean edges. No characters, no lettering, no UI. This is an independent scrolling background plane behind playable platforms.
