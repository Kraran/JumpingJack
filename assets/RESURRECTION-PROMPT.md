# Résurrection — symbole de vie en haute définition

Asset final : `life-symbol-hd-v1.png`, créé avec le **skill imagegen et l'outil intégré**, sans API externe. Référence : le faucon doré extrait de la poitrine du héros par `lives.load_life_symbol`, qui fournit aussi le symbole du HUD. L'image source extraite a été agrandie uniquement pour servir de référence à la reconstruction haute définition.

## Prompt exact

```text
Use case: identity-preserve. Edit the supplied reference, a low-resolution gold falcon emblem extracted from an Egyptian superhero's chest and used as the game's life HUD icon. Create a HIGH DEFINITION REMASTER of this EXACT emblem for a giant zoom animation. Keep the exact same asymmetric silhouette, orientation, proportions, pose and recognizable negative spaces. NOT a redesign: the left wing extends far up-left with a stepped feather edge, the right wing fans up-right and is shorter, the small falcon head and neck are near the top middle looking left, its long narrow torso and long pointed tail descend toward the bottom middle. Preserve the little gaps between feathers and beneath the wings, but resolve them into crisp clean intentional shapes rather than blurred pixel steps. One single emblem only. Reconstruct sharp engraved overlapping feather details, polished warm gold metal with soft amber shadows and restrained pale gold highlights, matching a realistic Egyptian fantasy game. Edges crisp and beautifully antialiased at 1536px, no pixelation or blur. Center the whole emblem with 8 percent transparent padding on all sides so no wing or tail is cropped. True transparent alpha background, NO halo, NO rays, NO glow baked into the image, NO ground shadow, NO letters, NO frame, no added symbols or gemstones. Preserve the source's overall shape faithfully so shrinking it back to HUD size reads as the same gold falcon chest symbol.
```

## Animation

La vie consommée est identifiée par son emplacement dans le HUD. Le faucon quitte exactement cet emplacement, s'agrandit jusqu'à 1240 pixels de large au centre du Full HD et déclenche un flash chaud. Le héros apparaît au point de reprise à 0,94 seconde, sous le pic lumineux, puis le flash se dissipe. La séquence complète dure 1,28 seconde. Le petit symbole d'origine est utilisé au début du trajet ; la version haute définition prend le relais pendant l'agrandissement. La mise à l'échelle est effectuée par le GPU, sans chargement de texture pendant le clip. Un halo radial est préparé au démarrage.

Le héros reste visible pendant la dissipation du flash. Les commandes et collisions sont neutralisées pendant la transition ; la pause et les sauvegardes conservent la phase exacte. Une mort par crocodile joue d'abord sa dévoration ; la dernière vie conduit au Game Over sans résurrection.

Reproduire l'aperçu : `python preview_resurrection.py --native-check`. Vidéo : `output/hero-resurrection-demo.mp4`. Mesures : `output/hero-resurrection-validation.json`.
