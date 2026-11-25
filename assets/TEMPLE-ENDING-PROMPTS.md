# Fin du niveau 03 — montée dans le sanctuaire

Deux assets créés avec imagegen intégré à partir de `hero-run-v3.png`, utilisé comme référence d’identité :
- `hero-stairs-turn-v1.png` : huit poses du profil droit vers la vue de dos.
- `hero-stairs-climb-v1.png` : 24 poses de montée lente, avec appuis alternés et cape animée.

L’ouverture de l’escalier remplit le rectangle (310, 272, 266, 508) de la porte 840 × 780 ; les marges noires latérales de l’ancien raccord sont recouvertes. Le héros atteint l’axe de l’escalier, se tourne puis monte six marches, jusqu’à mi-hauteur de l’escalier visible. Sa taille et son éclairage diminuent avec la profondeur ; il disparaît avant l’affichage du bilan. Durée totale : 4,32 secondes. Les poses intermédiaires, l’échelle et le fondu sont préparés au chargement dans un atlas 1960 × 4080, sans transfert de texture en cours d’animation.

La séquence suit le pas de simulation et se fige en pause. Les commandes de déplacement et de combat sont ignorées pendant la montée. La sauvegarde et le chargement conservent sa progression ; les anciennes sauvegardes restent lisibles. Les autres niveaux conservent leur sortie habituelle.

## Prompt : orientation vers l’escalier

```text
Reference is the game's exact hero: dark teal fitted suit, golden boots, wrist guards, belt and gold headband, short wavy black hair, red cape with gold trim. Preserve this identity and realistic game sprite style, no Superman S. Transparent production sprite sheet, full body in every cell, no background, no ground, no staircase (engine supplies it), no text, no labels, generous gutters, consistent scale and pivot at body center/feet. EXACTLY FOUR columns by TWO rows, eight chronological poses of a calm turn from RIGHT-facing profile standing/walking to REAR view facing straight AWAY into a doorway. Frame1 right profile, frames2-7 rotate gradually through right rear three-quarter, frame8 fully rear with shoulders horizontal and both boots visible. No mirrored paper squeeze; realistic torso depth, short planted pivot steps, natural arms, cape swings briefly sideways so legs remain visible. Feet on same baseline, smooth continuity. Camera fixed at standing human eye height, slightly above the boots.
```

## Prompt : montée de dos

```text
Reference is the game's exact hero: dark teal fitted suit, golden boots, wrist guards, belt and gold headband, short wavy black hair, red cape with gold trim. Preserve this identity and realistic game sprite style, no Superman S. Transparent production sprite sheet, full body in every cell, no background, no ground, no staircase (engine supplies it), no text, no labels, generous gutters, consistent scale and pivot at body center/feet. EXACTLY SIX columns by FOUR rows,24 chronological frames of a SEAMLESS slow stair-ascent cycle from FULL REAR view facing directly AWAY from viewer. The hero is walking UP shallow stone steps, never running: alternate lift a knee and place that boot on the next step, weight shifts onto the planted boot, trailing leg pushes up, then other knee rises. Slight forward torso lean, relaxed counter-swing of arms, realistic boot contacts and flexed ankles. Red cape hangs and sways sideways gently, leave knees and golden boots clearly visible. Consistent rear-facing camera, scale, identity, body mass, and registration across every equal cell. No profile poses in this sheet. Sprite position has no net upward movement through the sheet: game will move him upwards; only the natural small body bob and articulated climbing action. Frame24 returns smoothly to frame1.
```

Validation : tests de fin de temple, tests du niveau et des flammes, tests de sauvegarde, puis suite complète. `python preview_temple_ending.py --native-check` produit `output/temple-ending-demo.mp4`, les captures intermédiaires et `output/temple-ending-validation.json`.
