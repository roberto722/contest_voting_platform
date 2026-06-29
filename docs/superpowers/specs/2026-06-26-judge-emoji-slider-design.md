# Specifica di Design - Custom Emoji Slider per Voto Giudici

Questa specifica descrive l'implementazione di un range slider personalizzato per l'interfaccia dei giudici basato su Microsoft Fluent Emojis 3D, conforme alle indicazioni del CodePen fornito.

## Obiettivo
Sostituire il selettore numerico/range standard dei giudici con una barra di trascinamento premium in cui la maniglia (thumb) è rappresentata da un'icona Fluent Emoji 3D animata. L'icona visualizzata deve cambiare in modo proporzionale rispetto al punteggio massimo impostato per ciascun criterio.

## Dettaglio Tecnico

### 1. Componente React `EmojiSlider`
Creeremo il componente in `frontend/src/components/EmojiSlider.tsx`.

#### Funzionamento:
- Accetta le props:
  - `min: number` (punteggio minimo del criterio, es. 1)
  - `max: number` (punteggio massimo del criterio, es. 10)
  - `value: number` (punteggio corrente)
  - `onChange: (value: number) => void` (callback di aggiornamento)
- Calcola la percentuale di avanzamento:
  $$\text{percentage} = \text{max} > \text{min} ? \frac{\text{value} - \text{min}}{\text{max} - \text{min}} : 0$$
- Mappa la percentuale su 5 indici corrispondenti alle 5 icone Fluent Emoji 3D (0 a 4):
  $$\text{iconIndex} = \text{Math.round}(\text{percentage} \times 4)$$
- Le icone utilizzate saranno:
  - Indice 0: 🌱 **Seedling** (`https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Seedling/3D/seedling_3d.png`)
  - Indice 1: ✨ **Sparkles** (`https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Sparkles/3D/sparkles_3d.png`)
  - Indice 2: ⭐ **Star** (`https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Star/3D/star_3d.png`)
  - Indice 3: 🔥 **Fire** (`https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Fire/3D/fire_3d.png`)
  - Indice 4: 🏆 **Trophy** (`https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Trophy/3D/trophy_3d.png`)

#### Posizionamento:
- Il track esterno (`.slider-outer`) ha uno stile scuro/neutro coerente con l'area giudici.
- Il track interno di progresso (`.slider-inner`) si colora con un gradiente dinamico da arancione a giallo.
- L'emoji thumb (`.emoji-thumb`) si muove lungo l'asse X usando:
  - `left: ${percentage * 100}%`
  - `transform: translateX(-${percentage * 100}%)`
- Un input standard `<input type="range">` è posizionato sopra il track con `opacity: 0` per catturare tutti gli eventi di trascinamento e focus nativi.

### 2. Modifiche in `JudgePage.tsx`
Sostituiremo il tag `<input type="range" ... />` dentro il rendering dei criteri con il nuovo componente `<EmojiSlider />`.

### 3. CSS delle Classi in `styles.css`
Aggiungeremo i nuovi stili per `.slider-outer`, `.slider-inner`, `.emoji-thumb` e la gestione del focus e dell'input invisibile.

## Piano di Verifica
1. **Verifica Visiva**: Controllare il rendering delle icone 3D e il gradiente di riempimento.
2. **Verifica Criteri Variabili**: Testare con criteri aventi punteggio massimo differente (es. 5, 10, 3) per verificare la corretta proporzionalità delle icone.
3. **Verifica Interazione**: Testare trascinamento, click diretto sui punti del slider e cambio valore.
