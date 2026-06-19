# Podio finale Quasanremo — Design

## Obiettivo

Ridisegnare le modalità `show_podium` e `show_final_winners` affinché riproducano fedelmente il reference Quasanremo fornito: uno schermo teatrale nero e oro, leggibile da lontano, con podio 2–1–3, pannelli luminosi, pedane scenografiche e 4°/5° classificato.

Il reference è un target grafico vincolante, non una semplice ispirazione.

## Vincoli approvati

- Gli sfondi dei concorrenti restano generici per ora.
- Le capsule di stato non compaiono nel podio finale.
- Il 4° e il 5° classificato compaiono sotto il podio quando presenti.
- Nomi, posizioni e percentuali restano dati dinamici provenienti dall'API.
- Le altre modalità dello schermo pubblico non cambiano.

## Composizione

La schermata usa un artboard 16:9 centrato, scalato per entrare nel viewport senza deformazioni. Su rapporti differenti usa letterboxing e non produce scroll.

La gerarchia visiva è:

1. logo Quasanremo grande in alto a sinistra;
2. titolo `Podio finale` centrato, in serif oro, con sottotitolo;
3. podio centrale ordinato 2–1–3, con il primo posto più alto e dominante;
4. riga compatta per 4° e 5° posto;
5. messaggio di ringraziamento a fondo schermo.

## Strategia grafica

Generare un unico fondale 4K senza testo, persone o dati: palco nero/oro, spot teatrali, coriandoli, pentagrammi, ornamenti laterali e tre pedane vuote. Gli asset attuali non raggiungono la definizione del reference.

Sopra il fondale, React e CSS renderizzano:

- logo e titoli;
- tre pannelli concorrente con sfondo artista generico;
- badge 1, 2 e 3;
- nomi e percentuali;
- 4° e 5° posto;
- footer.

Questa separazione conserva l'impatto scenografico senza incorporare risultati variabili in un'immagine statica.

## Implementazione frontend

Riutilizzare i dati e il rendering già presenti in `ScreenArea`. Gli stili nuovi devono essere circoscritti alle classi delle modalità `stage-show_podium` e `stage-show_final_winners`.

Non introdurre componenti, dipendenze o astrazioni aggiuntive se non necessari. Il cambiamento minimo previsto interessa:

- `frontend/src/App.tsx` per il markup del podio;
- `frontend/src/styles.css` per composizione, scala e resa grafica;
- `frontend/public/quasanremo/schermo/` per il nuovo fondale.

## Dati e casi limite

- Nessuna modifica API o backend.
- Con uno, due o tre risultati, mostrare solo i posti disponibili senza buchi incoerenti.
- Mostrare 4° e 5° solo quando esistono.
- Se la somma dei punteggi è zero, mostrare `0,00%`.
- Impedire ai nomi lunghi di uscire dai pannelli tramite dimensionamento fluido e, come ultima difesa, ellissi.
- Senza risultati, mostrare `Risultati in preparazione` nello stesso linguaggio visivo.

## Verifica

- Eseguire la build frontend.
- Controllare il podio a 1920×1080 e 1366×768.
- Controllare un viewport non 16:9 per verificare letterboxing, assenza di deformazioni e assenza di scroll.
- Verificare i casi con 0, 1, 2, 3 e almeno 5 risultati.
- Verificare che le altre modalità dello schermo non abbiano regressioni visive.
