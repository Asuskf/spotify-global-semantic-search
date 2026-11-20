# DESIGN.md · front del buscador

Identidad: `brand-guidelines-seventech` (manda); craft y estados: `impeccable`; accesibilidad e interacción: `ui-ux-pro-max`.

- **Tokens**: `src/tokens.css` es copia de `assets/tokens/colors_and_type.css` de la skill (solo se antepone "Inter Variable" a `--st-font`). `src/circuit.svg` es el motivo de circuito de la skill. Sin hex fuera de esos dos archivos.
- **Tipografía**: Inter auto-hospedada con `@fontsource-variable/inter` (OFL, sin CDN). La variable llega a 900; la marca pide 950 en titulares, aquí se usa 850.
- **Logo**: `logo-seventech.png` no existe en la skill; se usa solo el wordmark de texto "SEVEN TECH / Python Guaranda". POR VERIFICAR: sustituir por el escudo oficial cuando el usuario lo aporte.
- **Degradado**: uno solo, la barra bajo el subtítulo. No hay texto con degradado (choca con impeccable) ni kicker.
- **Fondo claro**; navy solo en el botón primario y el wordmark. Datos del evento y CTAs de inscripción no se usan: el copy es el de la app.
- **Accesibilidad**: foco 3px `--st-focus` con offset 4px; objetivos ≥44px; borde de input en `--st-muted` (el borde `--st-input-border` da 1.43:1, no cumple 3:1); `aria-live` en estados; `prefers-reduced-motion`.
- **Otras versiones**: botón con `aria-expanded` (no `<details>`).
- **Contrato de pruebas**: atributos `data-testid` en `App.jsx`; no renombrar.
