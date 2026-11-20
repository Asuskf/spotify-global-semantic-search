---
name: brand-guidelines-seventech
description: >
  Aplica la identidad VISUAL oficial de SEVEN TECH 2026 (evento de tecnología presentado por
  Python Guaranda, Ecuador — seventech.softecsa.com) a cualquier entregable: escudo oficial de
  Python Guaranda, paleta navy + degradado cian→azul→violeta, tipografía Inter con titulares
  ultra-bold, circuito de nodos, póster de fecha. Úsala siempre que se cree o reestilice algo que
  deba verse como SEVEN TECH: landings HTML, slides, posters, flyers, posts sociales,
  certificados, credenciales, cronogramas, fichas de ponentes, dashboards de inscritos — aunque
  no digan "marca". También con "ponlo on-brand", "usa los colores de Seventech", "agrega el
  logo", "¿esto está en marca?", "revisa este diseño".
---

# SEVEN TECH 2026 — Guía de Marca Visual

> **Versión** 1.0 · **Actualizado** 2026-11-19 · **Fuente** `https://seventech.softecsa.com/`
> (hoja `assets/site.css`, tokens `:root`) + logo oficial · **Historial** `CHANGELOG.md`.

## AUTORIDAD DE ARCHIVOS — qué es canon

- `SKILL.md` — reglas vinculantes (este archivo).
- `assets/tokens/colors_and_type.css` — fuente única de color, tipo, radios, sombras.
- `assets/logos/logo-seventech.png` — escudo oficial (ver `assets/logos/README.md` si falta).
- `assets/motifs/circuit-art.svg` — motivo de circuito de nodos.
- `assets/templates/SEVENTECH_Landing_Starter.html` — punto de partida para HTML.

Nunca derives color, fuente o forma del logo desde fuera de estos archivos.

## Identidad

- **Evento:** SEVEN TECH 2026 (escritura alterna: `SEVENTECH 2026`). Presenta **Python Guaranda**.
- **Tagline:** *Tecnología que impulsa el futuro*
- **Frases de apoyo:** *Ideas que se comparten. Conexiones que construyen el mañana.* ·
  *Una comunidad. Muchas formas de crear.* · *Aprender. Compartir. Conectar.* ·
  *La tecnología se mueve. Muévete con ella.* · *Nos vemos donde nacen las próximas ideas.*
- **Datos:** Presencial 21 de noviembre de 2026 · Centro de Eventos Nacionales e
  Internacionales CENI UEB · Guaranda, Ecuador. En línea del 16 al 20 de noviembre de 2026.
  Participación gratuita · Presencial y virtual.
- **Ejes temáticos (en este orden):** Inteligencia artificial · Desarrollo de software ·
  Ciberseguridad · Más tecnología.
- **CTAs canónicos:** "Quiero participar" · "Inscríbete gratis" · "Explora el programa" ·
  "Forma parte del encuentro ↗" · "Reserva tu lugar gratis ↗".
- **Contacto:** info@softecsa.com · Web: seventech.softecsa.com
- **Idioma:** español (Ecuador), tuteo, frases cortas y cálidas. Fechas en formato largo:
  "21 de noviembre de 2026".

## ADHERENCIA — reglas duras (cada violación bloquea)

1. **Sin colores escritos a mano** fuera del archivo de tokens: usa `var(--st-…)`. Si un valor
   no existe como token, **para y avisa**.
2. **Una sola familia: Inter** (pesos 400 → 950). Nada de otra tipografía.
3. **Nunca dibujes, traces, recrees ni generes con IA el escudo de Python Guaranda.** Solo se
   coloca desde `assets/logos/logo-seventech.png`. Si no está, descárgalo de
   `https://seventech.softecsa.com/assets/logo-transparent.png` o pídeselo al usuario; mientras
   tanto usa solo el wordmark de texto y avisa.
4. **Fondo claro por defecto** (`--st-paper` / `--st-page-bg`). El navy es para bandas de
   énfasis (contador, llamada final, sidebar), no para la página entera.
5. **Un degradado protagonista por vista** (el "2026" del hero *o* un CTA destacado), más usos
   menores como líneas finas de 2px.
6. **Accesibilidad:** contraste ≥ 4.5:1 texto normal, ≥ 3:1 texto ≥ 18px o bold ≥ 14px;
   objetivos táctiles ≥ 44×44px; foco `outline 3px solid var(--st-focus)` + `offset 4px`;
   respeta `prefers-reduced-motion`.

---

## 01 — Logo

| Archivo | Qué es | Uso |
|---|---|---|
| `assets/logos/logo-seventech.png` (1254×1254, PNG transparente) | **Escudo de Python Guaranda**: blasón azul y blanco con edificios coloniales y la serpiente de Python (azul/amarillo) sobre una cinta | Header, footer, favicon, portadas, certificados, credenciales |

### Lockup (como en el sitio)

- Escudo + 13px de gap + texto en dos líneas:
  - `SEVEN TECH` — Inter **850**, 17px, `letter-spacing -0.04em`, `--st-navy`.
  - `Python Guaranda` — Inter **550**, 10px, `letter-spacing 0.03em`, `--st-muted`, 5px arriba.
- Tamaño del escudo: 49×58px (header), 34×40px (footer), 40×46px (sidebar navy, texto blanco y
  subtítulo `#adc3e3`). Siempre `object-fit: contain`. `alt="Python Guaranda"`.
- **Wordmark hero:** `SEVEN` / `TECH <em>2026</em>`, Inter **950**, `letter-spacing -0.075em`,
  `line-height 0.91`, segunda línea al 77%; `2026` con el degradado recortado al texto.

### Reglas

- Espacio libre mínimo = ¼ del ancho del escudo.
- No deformar, rotar, recolorear, desaturar, añadir sombra/contorno ni recortar la cinta.
- Sobre navy, si pierde contraste, colócalo en una loseta blanca de radio 12px. Nunca sobre
  fotos cargadas ni sobre el degradado.
- El escudo es de **Python Guaranda** (organizador); no inventes un isotipo para SEVEN TECH.

---

## 02 — Paleta de color

Tokens completos en `assets/tokens/colors_and_type.css`.

| Nombre | Token | Hex | Rol |
|---|---|---|---|
| **Navy** | `--st-navy` | `#082b68` | Marca, botones primarios, bandas oscuras, títulos |
| Ink | `--st-ink` | `#0a2c68` | Texto principal |
| Muted | `--st-muted` | `#52698e` | Párrafos, texto secundario |
| Line | `--st-line` | `#dce6f4` | Bordes y divisores |
| Paper | `--st-paper` | `#fbfcff` | Fondo de página |
| **Azul** | `--st-blue` | `#087cff` | Kicker, enlace activo, iconos |
| **Cian** | `--st-cyan` | `#00c7f5` | Puntos de estado, inicio del degradado |
| **Violeta** | `--st-purple` | `#8a2cff` | Fin del degradado, año, sellos |
| Degradado | `--st-gradient` | `110deg #00c7f5 → #387bff 52% → #8a2cff` | Año hero, líneas, 1 CTA |

**Proporción:** ≈ 75% claros (Paper, blanco, tintes) · ≈ 20% Navy/Ink · ≈ 5% acentos.

### Contraste verificado (WCAG)

| Color | Sobre blanco | Uso permitido |
|---|---|---|
| Navy `#082b68` | 13.5:1 ✅ | Todo texto |
| Muted `#52698e` | 5.6:1 ✅ | Párrafos, notas |
| Violeta `#8a2cff` | 5.4:1 ✅ | Texto de acento |
| Azul `#087cff` | 3.9:1 ⚠️ | Solo texto ≥ 18px o bold ≥ 14px, iconos |
| Cian `#00c7f5` | 2.0:1 ❌ | **Nunca texto sobre claro**: puntos, líneas, decoración |
| Cian sobre Navy | 6.7:1 ✅ | Acento en bandas oscuras |
| `#cbdcf6` sobre Navy | 9.7:1 ✅ | Texto secundario en bandas oscuras |

### Reglas de color

- **Una idea = un color:** navy = marca/acción; azul = enlace/info/kicker; cian = "en vivo"/
  estado; violeta = año, sellos, destacados.
- Ejes temáticos: IA → azul (`--st-tint-blue`), Software → violeta (`--st-tint-violet` +
  `--st-violet-text`), Ciberseguridad → turquesa (`--st-tint-teal` + `--st-teal-text`),
  Más tecnología → azul.
- Botón con degradado: texto blanco 750, tamaño ≥ 14px; para botones pequeños usa navy (el
  extremo cian no da contraste con blanco).
- Estados siempre con texto ("Confirmado", "Pendiente"), nunca solo color.

---

## 03 — Tipografía

**Inter** es la única familia (`var(--st-font)`). PPTX/DOCX: Inter instalada o embebida
(SIL OFL); si no está disponible, Segoe UI / Arial como respaldo y avisa.

| Nivel | Tamaño | Peso | Detalles |
|---|---|---|---|
| Hero | `clamp(60px,7.8vw,106px)` | **950** | `ls -0.075em`, `lh 0.91` |
| Fecha gigante | 106px | 900 | `ls -0.08em`, mes vertical 15px/600 (`writing-mode: vertical-rl; rotate(180deg)`) |
| H2 sección | `clamp(30px,3.4vw,46px)` | 800 | `ls -0.045em`, `lh 1.13`, suele ir en 2 líneas |
| H3 tarjeta | 18–24px | 700 | `ls -0.025em` |
| Tagline | 19px | 700 | navy |
| Kicker | 14px | 700 | azul, `ls 0.015em`, caja normal |
| Cuerpo | 16–18px | 400 | `lh 1.6–1.7`, muted |
| Nav | 13px | 600 | navy, hover azul |
| Botón | 14–16px | 750 | |
| Pill | 11px | 650 | radio 6px |
| Números (contador/KPI) | 30–32px | 700 | `tabular-nums`, `ls -0.05em` |

Firma: **pesos extremos** (950 vs 400) y **tracking negativo** en titulares. Títulos en caja
normal, salvo el wordmark.

## 04 — Motivos gráficos

- **Circuito de nodos** (`assets/motifs/circuit-art.svg`): líneas `#56aaff` 1.2px, nodos
  relleno `#f9fcff` borde `#9254f4` 1.7px, opacidad 0.4. Fondo ligero; nunca encima del logo
  ni del texto principal.
- **Orbes de esquina:** `--st-page-bg` (cian arriba-derecha, violeta abajo-izquierda).
- **Línea de presentación:** barra 28×2px con degradado + "Python Guaranda presenta".
- **Glifos:** `✦` azul en notas · `✓` azul 800 en beneficios · `↗` en CTAs externos ·
  `+ / −` en FAQ · punto de estado 6px cian.
- **Indicador en vivo:** círculo 24px borde `#62b1ec` con punto interior azul.
- Iconos de línea (stroke 2, `currentColor`) en cuadros de 47px radio 12px con tinte.

## 05 — Componentes

| Componente | Receta |
|---|---|
| **Header** | sticky 87px, `#fbfcfff5` + `blur(14px)`, borde inferior line; CTA "Inscríbete gratis" navy radio 10px |
| **CTA primario** | navy, texto blanco 750, radio 14px, alto ≥ 52px, icono `↗` en cuadro cian claro `#b9efff` |
| **CTA degradado** | `--st-gradient`, radio 9px, padding 15×25, `--st-shadow-btn`, hover `translateY(-1px)` |
| **Botón outline** | blanco, texto navy, borde `#c8d8ed` |
| **Póster del evento** | `--st-poster`, borde `--st-border-strong`, radio 26px, `--st-shadow-poster`, circuito de fondo, "26" violeta, fecha gigante + mes vertical, lugar, bloque "en línea" |
| **Banda contador** | navy radio 20px; casillas borde blanco 15% fondo blanco 5%; números blancos; etiquetas `#cbdcf6` 10px; `:` cian |
| **Grid de ejes** | 4 columnas en tarjeta blanca borde line radio 16px, divisores internos, icono tintado |
| **Tarjeta ponente** | imagen 280px radio 16px, placeholder `linear-gradient(135deg,#dbefff,#e9dcfc)` con inicial 100px `#a5c3ea`; pill blanca con el tema |
| **Pill** | 11px/650, padding 5×10, radio 6px, fondo `#edf5ff`, borde `#cfe0f6`, texto `#15559f` |
| **Tabs agenda** | borde line radio 7px; activo navy/blanco |
| **Formulario** | tarjeta blanca radio 18px padding 35px `--st-shadow-card`; inputs radio 7px borde `#cbd9ec`; label 12px/600 |
| **Certificado** | sección `--st-cert-bg`; hoja blanca rotada −7°, borde superior 6px `#29a7f7`, sello circular violeta |
| **Llamada final** | banda navy radio 20px padding 45×50, H2 blanco 35px, CTA degradado |
| **Footer** | lockup pequeño + email + enlaces 11px, borde superior line |

## 06 — Layout

- Contenedor `min(1180px, 100% - 64px)`; móvil `100% - 48px`.
- Secciones con padding vertical 100px (70px móvil). Encabezado: kicker + H2 a la izquierda,
  párrafo de 450px a la derecha.
- Hero: grid `1.23fr 1fr` (texto | póster), gap 75px.
- Orden de landing: Header → Hero + Póster → Contador → Ejes → Ponentes → Auspiciantes →
  Concursos → Cronograma → Ubicación → Certificado → Inscripción + FAQ → Llamada final → Footer.
- Ritmo de fondo: Paper ↔ `--st-surface-alt`; bandas navy como pausa.

## 07 — Motion

Sutil: hover `translateY(-1px)` + sombra en 0.15s; scroll suave; contador en vivo. Con
`prefers-reduced-motion`, sin transformaciones ni animaciones.

## 08 — Aplicación por formato

- **HTML / landing:** parte de `assets/templates/SEVENTECH_Landing_Starter.html`; tokens del
  CSS; logo desde archivo (o data-URI). Sin frameworks CDN.
- **Slides 16:9:** fondo Paper con orbes; portada = wordmark + póster de fecha; contenido con
  kicker azul + H2 navy 800; cierre en banda navy "Nos vemos donde nacen las próximas ideas."
  Lockup arriba a la izquierda.
- **Poster / flyer / post:** lockup, wordmark, tagline, fecha gigante con mes vertical, lugar,
  "Participación gratuita · Presencial y virtual", CTA y `seventech.softecsa.com`; circuito de
  fondo. Formatos 1080×1350, 1080×1080, 1080×1920.
- **Certificado:** A4 horizontal, blanco con borde superior degradado, escudo arriba, nombre
  Inter 900, sello violeta, fecha y lugar oficiales.
- **Credencial / ticket:** código en azul 750 `ls 0.03em`; datos `dt` muted / `dd` ink.
- **DOCX / PDF:** títulos Inter 800 navy, cuerpo 11pt en Ink, tablas con encabezado `#f9fbfe`
  y bordes `#e6edf7`.

## 09 — Visualización de datos

- Fondo blanco o Paper; rejilla line; ejes 12px muted.
- Series: **Navy → Azul → Violeta → Turquesa `#087b99` → Muted**. Cian solo para destacar
  sobre fondo navy.
- KPI: tarjeta borde line radio 10px, etiqueta 12px muted, número 32px 700.
- Etiquetas directas; nunca el color como única codificación.

## 10 — Revisión de diseño (checklist)

1. **Accesibilidad:** contrastes de §02 (azul y cian sobre claro), foco visible, táctiles,
   alt del logo.
2. **Marca:** tokens sin hex sueltos, solo Inter, escudo desde archivo sin alterar, un
   degradado protagonista, datos del evento correctos.
3. **Craft:** jerarquía 950/800/400, tracking negativo, aire generoso, bordes finos en vez de
   sombras pesadas.
4. **Contenido:** tuteo, CTAs canónicos, frases cortas.

Reporta hallazgos como *Qué / Por qué / Arreglo* con severidad (crítico, mejora, detalle).

## Referencia rápida

**Evento**: SEVEN TECH 2026 · presenta Python Guaranda · *Tecnología que impulsa el futuro*
**Núcleo**: Navy `#082b68` · Ink `#0a2c68` · Muted `#52698e` · Line `#dce6f4` · Paper `#fbfcff`
**Acentos**: Azul `#087cff` · Cian `#00c7f5` · Violeta `#8a2cff`
**Degradado**: `linear-gradient(110deg,#00c7f5,#387bff 52%,#8a2cff)`
**Tipo**: Inter (400–950), titulares con tracking negativo
**Logo**: escudo Python Guaranda — `assets/logos/logo-seventech.png`
**Estilo**: claro · limpio · tecnológico · circuito de nodos · un degradado por vista · AA siempre
