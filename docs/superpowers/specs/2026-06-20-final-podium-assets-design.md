# Podio finale con asset Quasanremo

## Obiettivo

Allineare esclusivamente le modalita schermo `show_podium` e
`show_final_winners` alla reference `Immagine_reference_schermo_1.png`, usando
gli asset gia presenti in `frontend/public/quasanremo/schermo`.

Gli altri stati dello schermo restano invariati.

## Composizione

- Mantenere lo sfondo scenico `podium-stage-4k.png` in formato 16:9.
- Disporre i primi tre classificati nell'ordine visivo 2-1-3.
- Usare `podium_panel_1_gold_clean.png`,
  `podium_panel_2_silver_clean.png` e
  `podium_panel_3_bronze_clean.png` come cornici reali dei concorrenti.
- Usare `podium_base_1_gold.png`, `podium_base_2_silver.png` e
  `podium_base_3_bronze.png` come piedistalli reali.
- Inserire dentro ogni pannello lo sfondo del partecipante, il nome e la
  percentuale calcolata. La cornice PNG resta sopra lo sfondo.
- Mantenere quarto e quinto classificato nelle due fasce inferiori gia
  predisposte nello sfondo.
- Allineare titolo, sottotitolo, logo, footer e spaziature alla reference.

## Dati e comportamento

La sorgente dati non cambia: risultati, ordinamento e percentuali continuano a
provenire da `ScreenArea`. Il podio resta dinamico e supporta nomi lunghi con
troncamento, senza introdurre nuovi endpoint o dipendenze.

In assenza di risultati resta visibile il messaggio esistente. In assenza di
un'immagine specifica del partecipante viene usato il backdrop gia disponibile.

## Implementazione minima

Modificare il markup del solo podio in `frontend/src/App.tsx` e le relative
regole in `frontend/src/styles.css`. Riutilizzare gli asset esistenti; non
generare immagini e non modificare backend, realtime o modalita schermo diverse
dal podio finale.

## Verifica

- Eseguire i test frontend esistenti relativi all'ordinamento e alle percentuali.
- Eseguire build o type-check del frontend.
- Acquisire uno screenshot 16:9 della modalita podio e confrontarlo con la
  reference, verificando asset, ordine 2-1-3, leggibilita e assenza di overflow.
