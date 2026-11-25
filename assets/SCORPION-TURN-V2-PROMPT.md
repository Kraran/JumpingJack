# Exécuteur : retournement en volume

Asset : `scorpion-executor-turn-v2.png`, créé avec imagegen intégré à partir de la capture du jeu `output/scorpion-walking.png` comme référence d’identité.

24 vues réelles du profil droit au profil gauche en passant par la face. Le robot garde sa largeur, ses huit appuis, ses deux pinces et sa queue complète. Le pivot dure 0,48 seconde et suit une accélération puis décélération douce. Les vues inverses sont préparées au chargement, ainsi que les textures GPU. L’ancienne compression horizontale du sprite est supprimée.

## Prompt exact

```text
Create a production transparent sprite animation atlas for the EXACT black robot scorpion visible in the attached game screenshot. Reference role: identity only, ignore temple, hero, HUD. Heavy angular black gunmetal armor, red vents, powerful serrated pincers, eight mechanical legs, curled segmented tail ending in a SHORT HORIZONTAL LASER CANNON, never an organic stinger. Show the COMPLETE scorpion including tail and cannon in every cell. EXACTLY 6 columns by 4 rows = 24 chronological frames, read left-to-right top-to-bottom. This is a genuine volumetric 180 degree on-the-spot turnaround, NOT a 2D squeeze or mirror: frame 1 strict RIGHT profile, frames 2-6 right three-quarter increasingly facing viewer, frames 7-12 near frontal, frames 12-13 fully frontal with wide spread legs and two broad pincers clearly separated horizontally, frames 14-19 left three-quarter, frame24 strict LEFT profile. Rotation smooth and monotonic through front view, body retains its realistic thickness and broad leg spread at midpoint. Scorpion walks its eight legs around its planted body center with short alternating support steps, no sliding, tail naturally counterbalances and sweeps in depth, pincers arc around body in 3D. Same identity, materials, rigid body volume, fixed orthographic camera elevation slightly above floor, fixed framing and scale in all cells, baseline and rotation center registered. First and last profile should match reference silhouette and low curled tail. No pinched flat paper middle frame. No scale or perspective changes, no clipping. Equal cells, generous transparent gutters, no cell borders, no text or numbering, no ground or shadows, truly transparent background. High-detail realistic SF game art. Large canvas 1536x1024 or larger.
```

Validation : `python -m unittest discover -s tests -p test_scorpion.py -v` ; `python preview_scorpion.py --native-check --turn-only` pour la démonstration des deux sens en Direct3D 11 et `output/scorpion-turn-validation.json`.
