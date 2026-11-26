# Mort par chute dans un trou

Asset : `assets/hero-pit-death-v1.png`, créé avec imagegen intégré. Référence d’identité : `hero-laser-death-v1.png`. Une seconde passe imagegen a remplacé le fond clair du premier résultat par une vraie transparence ; le résultat final est conservé sans retouche.

Séquence rapide de 0,75 s : fondu depuis la pose aérienne pendant 0,10 s, bras levés puis boucle de panique pendant la chute. La cape remonte sous l’effet de l’air. Les 16 poses dessinées donnent 64 images par sens, préchargées ; les poses et le retour de boucle sont interpolés. La position descend avec la vitesse initiale et une accélération, sans déplacer artificiellement la caméra. Le déclenchement a lieu dès le franchissement irréversible du bord du trou, avant la sortie d’écran ; les chutes normales et la noyade gardent leurs règles.

Vibration pendant toute la séquence, commandes bloquées, pause et sauvegardes prises en charge. Résurrection ou Game Over à la fin du clip.

Aperçu : `python preview_pit_death.py`.

## Prompt de dessin

Use case: stylized-concept. Asset: transparent 4x4 sprite sheet, sixteen sequential frames for a realistic side-view platform game. Reference image supplies ONLY hero identity and painterly game style: athletic black-haired masked Egyptian superhero, dark teal bodysuit, gold falcon chest emblem, gold boots and gauntlets, red cape. NEW animation: falling helplessly into a pit, frantically waving both arms up in the air. No injuries, fire, smoke or electricity. All figures face RIGHT, strict side profile, same character scale and same foot/root alignment in equal square cells. Frames 1-4 transition from relaxed ordinary falling pose with hands low to startled upright falling, shoulders rising and both arms lifting above the head. Frames 5-16 form one seamless loop: frightened face looking upward, both arms flailing above/beside his head alternately, hands open, torso gently rocking, knees slightly bent and legs dangling, cape streaming UP from the falling airflow. Frame 16 flows back into frame 5. The HERO FALLS FEET FIRST, never lands, kneels or lies down. Keep body proportions and scale identical throughout; don't stretch the arms. Include whole arms and cape inside each cell with generous empty gutters. Four columns and four rows, no labels or grid. True alpha transparent background, no ground, no shadows, no props. Polished anatomically natural motion with enough pose differences to read at small game size.

## Correction de transparence

Edit ONLY the background of this exact sprite sheet. Remove the pale white/checkered background completely to TRUE TRANSPARENT ALPHA (alpha=0) everywhere outside the superhero. Preserve all sixteen superhero poses, their positions, shapes, cape, colors, proportions, face and every detail. Keep a clean transparent border around every pose and between cells. Do not draw a checkerboard or a white background: export genuine transparency. No new objects or text.
