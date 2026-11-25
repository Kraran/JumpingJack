# Escalier du sanctuaire — niveau 03

Asset : `temple-sanctuary-stairs-v1.png`, créé avec imagegen intégré. La porte existante rendue dans `output/temple-gate-before.png` sert de référence pour les matériaux et l’éclairage.

L’image remplit uniquement l’ouverture intérieure de la porte finale, dans le rectangle (310, 272, 266, 508) de l’image de porte 840 × 780. Les montants sculptés, le linteau et le passage existant sont conservés. L’escalier s’enfonce en perspective : les premières marches sont éclairées par la salle, les suivantes disparaissent dans le noir. Le décor est composé au chargement dans la texture de porte, sans nouvelle opération de rendu par image.

## Prompt exact

```text
Create ONLY the interior view to insert into the dark rectangular opening of the Egyptian temple doorway shown in the reference. Reference role: sandstone material and warm lighting context only. Do NOT redraw any part of the doorway frame, lintel, winged sun, columns, statues or hieroglyphs. Deliver an opaque tall narrow portrait panel, aspect ratio1:2, ideally512x1024. A worn ancient Egyptian stone staircase starting across the full width of the bottom edge and receding upwards into a completely dark interior corridor. About12 broad shallow sandstone steps, realistic chipped edges and subtle sandy roughness, first3steps readable in dim amber light spilling in from outside, next steps progressively darker and narrower in perspective, upper steps disappearing naturally into almost total blackness. Staircase begins exactly at bottom edge, no landing, no gate, no exterior scenery, no people, no torches, no light source at far end. Upper half should be overwhelmingly deep warm black, not a lit corridor or visible destination. Subtle converging shadowed sandstone sidewalls only in lowerhalf, black edges at top and sides that blend seamlessly into the existing black doorway. Straight-on view from the threshold at human height; coherent realistic perspective, atmospheric sense of depth. Photorealistic cinematic game background, crisp believable stone steps near viewer, dark subdued colors, no exaggerated orange glow, no UI, no text, no borders. Fill entire panel, NO transparency.
```

Validation : huit tests du niveau 03, puis approche et franchissement de la sortie avec la physique réelle sous Direct3D 11. Capture : `output/temple-sanctuary-stairs.png` ; mesures : `output/temple-stairs-validation.json`.

La montée finale du héros est décrite dans [TEMPLE-ENDING-PROMPTS.md](TEMPLE-ENDING-PROMPTS.md). Le niveau se termine après sa disparition dans l’obscurité.
