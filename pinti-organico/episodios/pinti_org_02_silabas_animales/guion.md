# Guion: "M con U… ¡MUUU!" (las sílabas de los animales)

- **Slug:** `pinti_org_02_silabas_animales`
- **Pilar:** historia (sketch de humor con sílabas, repetición + error tierno)
- **Formato:** 1080x1920, 30 fps. Sin fades a negro.
- **Assets reales:** `paginas/pagina-21.jpg` (Sílabas con M), `paginas/pagina-24.jpg` (Sílabas con P, solo la tarjeta "pe" y "p + a = pa" como modelo de fórmula), `ilustraciones/pag52_212.png` (vaca), `ilustraciones/pag52_214.png` (gato), `ilustraciones/pag36_163.png` (pato Pepe), `pinti.png`, `portada.jpg`.
- **Tarjetas de sílaba:** se recortan de las páginas reales o se replican con su mismo estilo (ma naranja, me azul, mi verde, mo amarillo, mu rosa; pe azul de la pág. 24). Siempre en minúscula y con la misma tipografía redondeada del libro.

## Decisión sobre Pepe y la "pe"

**La uso.** Dentro de la M, Pepe no tiene una sílaba que le encaje. Con "pe" el chiste se cierra solo: Pepe no sabe leer la sílaba de su propio nombre. Para que no se mezclen la M y la P (revisado por la pedagoga):
1. **El nombre de la letra P nunca se dice en voz.** "Pe" (el nombre de la letra) suena igual que la sílaba "pe" y confundiría al niño. Pinti dice "¡Ahora, la letra de Pepe!". La P solo aparece en pantalla: la cabecera cambia de forma visible de "Sílabas con M" a "Sílabas con P" y sale la fórmula "p + e = ?".
2. Las tarjetas de la M se apartan y entra sola la tarjeta azul "pe" de la pág. 24, con la fórmula "p + e = pe" en pantalla, que es el mismo formato que "m + a = ma" de la pág. 21.
3. La corrección se ancla en algo que el niño ya conoce, su nombre: "pe · pe" en minúscula azul (como la tarjeta) se une en "Pepe".
4. Pinti dice siempre las sílabas cortas y limpias ("mu", "mi", "pe"). Lo largo o lo incorrecto ("MUUU", "miau", "CUAC") solo lo dicen los animales. El ✔ va solo sobre "m + u = mu", nunca sobre "MUUUU".
5. Con la M se enseña a juntar sonidos con el truco del "mmm" (la M se puede alargar sin cambiar su sonido). Con la P no se hace, porque su sonido no se puede alargar.
6. El remate vuelve a la M (pág. 21 completa), así que el vídeo empieza y termina en la misma letra.

**Locución (TTS):** el texto de las voces va con las sílabas en minúscula y entre exclamaciones ("¡mu!", "¡mi!", "¡pe!"), nunca en mayúscula, para que no se lean como siglas ("eme u", "pe e"). Antes de montar hay que escuchar cada toma: "mu", "mi" y "pe" tienen que sonar cortas, sin vocal de más y sin el nombre de la letra delante. Si una toma sale mal, se repite solo esa sílaba.

## Escaleta

| t_inicio | t_fin | voz (quién + texto) | texto en pantalla | qué se anima | SFX |
|---|---|---|---|---|---|
| 0,0 | 1,8 | [VOZ PINTI] "¿Cómo suena la M con la U?" | **¿Cómo suena la M con la U?** (arriba, entra palabra a palabra con la voz) | Frame 0: Pinti ya está en plano, de cerca, sosteniendo la tarjeta "m" en una mano y la "u" en la otra. Las choca y se funden en la tarjeta rosa "mu" con un pequeño rebote. Cámara con leve zoom-in. | pop suave al fundirse las tarjetas (frame del choque) |
| 1,8 | 3,4 | [VOZ VACA] "¡MUUUU!" | **MUUUU** (letras grandes que vibran con la voz) | La vaca entra desde la derecha a saltitos. Le rebota la campana y mueve las orejas. Al mugir, se le estira la boca (squash & stretch) y Pinti sale despeinado hacia atrás por el "viento". | campanita en cada salto + boing al aterrizar |
| 3,4 | 4,6 | [VOZ PINTI] "¡Mmm… u… ¡mu!" | **m + u = mu** ✔ (check verde dibujado solo sobre la fórmula; "MUUUU" ya desapareció) | La tarjeta "mu" se separa en "m" y "u". Mientras suena "mmm", la tarjeta "m" vibra; con la "u" se juntan de nuevo y vuelven a ser "mu". La tarjeta brilla, Pinti choca la pezuña de la vaca y salen unas estrellas amarillas como las de "¡Lo logré!". | zumbido suave en la vibración de la "m" + ding de acierto al unirse |
| 4,6 | 5,8 | [VOZ PINTI] "¿Y la M con la I?" | **m + i = ?** | Whip-pan lateral rápido: la vaca sale y aparece la tarjeta verde "mi". Pinti la levanta mirando a la izquierda. | whoosh del barrido |
| 5,8 | 6,9 | [VOZ GATO] "¡Miau!" | **miau** (minúscula) | El gato asoma desde abajo del encuadre, sube de golpe y se sienta. Mueve la cola y parpadea. | pop de aparición |
| 6,9 | 8,6 | [VOZ PINTI] "Casi… ¡es mi!" | **mi~~au~~** → queda **mi** | Gag visual: la "a" y la "u" de "miau" se despegan y caen rebotando al suelo. Queda "mi", que encaja letra por letra sobre la tarjeta verde "mi". El gato mira las letras caídas, sorprendido. | plin-plin de las dos letras al caer (una por letra, en el frame de impacto) |
| 8,6 | 11,0 | [VOZ PINTI] "¡Ahora, la letra de Pepe! ¿Cómo dice esta?" | Cabecera: **Sílabas con M** → **Sílabas con P** · debajo: **p + e = ?** | Al decir "la letra de Pepe", la cabecera gira como una tarjeta y cambia de letra (la P solo se ve, no se nombra). Las tarjetas de la M se apartan y entra sola la tarjeta azul "pe" (pág. 24). Con "¿Cómo dice esta?" Pinti la señala. Pepe entra deslizándose sobre su charquito de agua con las ondas animadas. | flip de la tarjeta + chapoteo suave cuando entra Pepe |
| 11,0 | 12,0 | [VOZ PEPE] "¡CUAC!" | **CUAC** (letras amarillas que saltan) | Pepe lo dice con todo el pecho y el agua salpica. Pinti se queda congelado medio segundo con los ojos muy abiertos (beat cómico). | splash pequeño, sincronizado con el "CUAC" |
| 12,0 | 14,6 | [VOZ PINTI] "¡Nooo, Pepe! Dice… ¡pe! ¡Como tu nombre!" | **p + e = pe** (solo visual: se ilumina "p", luego "e" y luego "pe") → luego **pe · pe** en minúscula azul, que se une en **Pepe** | Pinti se lleva las manos a la cabeza y luego señala la tarjeta. Con "Dice…" se iluminan la "p" y la "e" y, con "¡pe!", la "pe". Con "¡Como tu nombre!" aparece "pe · pe" encima de Pepe, las dos sílabas se acercan y se juntan en "Pepe". | ding al "¡pe!" + dos tics al aparecer cada "pe" + pop suave al juntarse |
| 14,6 | 15,8 | [VOZ PEPE] "Pe… ¡Pepe!" | **Pepe** ✔ | Pepe entiende, da una vuelta feliz en el agua y aletea. | sparkle + aleteo suave |
| 15,8 | 18,6 | [VOZ PINTI] "¿Tu hijo lo dice bien… o hace como Pepe?" | **¿Tu hijo lo dice bien… o hace como Pepe?** | Corte a la **pág. 21 real a pantalla completa** con zoom lento sobre "ma me mi mo mu". Cada tarjeta da un pequeño salto en secuencia. Pinti en una esquina (zona segura) le guiña a cámara y Pepe asoma por el borde. | pops muy suaves en cascada, uno por tarjeta |
| 18,6 | 21,8 | [NARRADORA] "Lo encuentras en el link de mi perfil." | **Aprende a leer y escribir con Pinti** · **Link en el perfil** (bloque centrado en la zona segura, aprox. y=1150–1400, nunca en el tercio inferior) | La pág. 21 se desliza al fondo y entra la **portada real** al frente, con un leve balanceo 3D. Pinti, la vaca, el gato y Pepe se asoman alrededor y saludan. El último frame vuelve a Pinti con la tarjeta "mu" para que el bucle empalme con el inicio. | campanita de la vaca, suave, como cierre |

## Duración total estimada

- **≈ 21,8 s** (dentro del rango 18–25 s).
- Narradora (Liz): solo el CTA, 8 palabras ≈ 3,1 s a 2,6 palabras/s.
- Hay una recompensa cómica o visual cada 1,5–3 s: el choque de las tarjetas, el MUUU, el truco del "mmm", el gato, la caída de las letras, el cambio a la P, el CUAC, "pe · pe" que se une en "Pepe" y la página real.

## Notas de voz y sonido

- [VOZ PINTI]: voz infantil (niño o niña de 5–6 años), alegre y rápida, en español LATAM neutro. Dice las sílabas cortas y limpias, sin alargarlas.
- [VOZ VACA], [VOZ GATO], [VOZ PEPE]: tres voces propias de caricatura, bien distintas entre sí y de la de Pinti. La vaca es grave y alargada, el gato agudo y corto, y Pepe es ronquito y entusiasta.
- [NARRADORA]: Liz (Sweet & Warm Storyteller), cálida, solo en el CTA.
- El precio no aparece en la voz ni en pantalla.
- Los SFX van siempre entre 10 y 14 dB por debajo de la voz (que va a ≈ -14 LUFS) y sincronizados al frame indicado. Sin música de fondo o, si la hay, muy baja (≥ 14 dB por debajo).

## Ganchos alternativos (test A/B)

1. **Arranque en frío con la vaca.** [VOZ VACA] "¡MUUUU!" desde el frame 0, con el texto **"Esta vaca ya sabe leer sílabas"**. Después Pinti: "¡Mmm… u… ¡mu!", con el truco de la tarjeta "m" vibrando, y se sigue igual desde 4,6 s.
2. **Para los padres, con dolor.** [NARRADORA] "¿Tu hijo ya junta la M con la U?" con el mismo texto en pantalla, mientras se funden las tarjetas "m" y "u". La vaca entra a 1,8 s.
3. **Empezar por el error.** [VOZ PEPE] "¡CUAC!" en el frame 0, con el texto **"Pepe no sabe leer su propio nombre"**. Pinti: "¡Nooo, Pepe! Mira…" y flashback rápido a la vaca. Pepe vuelve en el tramo de la P, con los mismos textos corregidos ("¡Ahora, la letra de Pepe!" / "Dice… ¡pe!"), y la P sin nombrarse en voz.
