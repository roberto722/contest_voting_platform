# Restyling e separazione del voto pubblico

Data: 2026-06-19

## Obiettivo

Separare l'area di voto pubblico dall'interfaccia amministrativa e applicare il tema Quasanremo fornito in `C:\Users\r.scardigno\Desktop\quasanremo_assets`. La nuova pagina deve essere mobile-first, mantenere tutti i metodi di voto esistenti e risultare coerente con `immagine_reference.png`.

## Routing e isolamento

- La pagina pubblica usa `/vote`.
- `/vote?competitionId=<id>` apre direttamente la competizione e richiede il PIN solo quando configurato.
- `/vote` senza `competitionId` mostra il form di accesso con codice competizione e PIN opzionale.
- Il bootstrap frontend decide subito tra applicazione amministrativa e pagina pubblica. La pagina pubblica non monta topbar, selettore delle aree o stato dell'admin e non avvia i caricamenti amministrativi.
- I link e QR generati dall'admin vengono aggiornati al nuovo formato `/vote?competitionId=<id>`.
- Non viene aggiunto un router: il controllo di `window.location.pathname` è sufficiente per queste due entry point.

## Struttura frontend

- Estrarre l'attuale `PublicArea` da `App.tsx` in un componente pubblico dedicato.
- Aggiungere un foglio stile dedicato, caricato dal componente pubblico, così il tema Quasanremo non altera admin, giudici o schermo.
- Riutilizzare l'helper HTTP e i contratti API già presenti; il backend non cambia.
- Rimuovere l'accesso "Pubblico" dal selettore interno dell'app admin perché la pagina è raggiungibile solo dal nuovo indirizzo.

## Direzione visiva approvata

È approvata la variante B, mobile-first compatta:

- sfondo verticale Quasanremo su telefono e sfondo desktop sui viewport larghi;
- logo centrato e compatto;
- titolo e contesto della competizione sopra le opzioni;
- stato della votazione visibile come badge;
- partecipanti in lista a colonna singola, con numero progressivo, fondale artistico e selezione dorata evidente;
- pulsante "Conferma voto" largo e sempre facilmente raggiungibile;
- layout desktop centrato con larghezza controllata, senza trasformarlo nella griglia larga del riferimento.

I fondali dei partecipanti vengono assegnati per posizione usando i cinque asset disponibili, senza associare nomi specifici nella logica. Il dominio resta generico.

## Asset

Gli asset necessari vengono copiati sotto gli asset statici del frontend mantenendo nomi leggibili. Sono sufficienti:

- `backgrounds/bg-public-desktop.png`
- `backgrounds/bg-public-mobile.png`
- `backgrounds/texture-dark-noise.png`
- `brand/logo-rectangular-transparent.png`
- `artists/artist-bg-01.webp` ... `artist-bg-05.webp`
- icone `waiting.svg`, `success.svg`, `closed.svg`, `error.svg`, `lock.svg` e `vote.svg`

Glow, bordi, pulsanti e transizioni vengono realizzati in CSS. Non servono immagini generate né nuove dipendenze.

## Flusso dati e stati

1. L'utente apre `/vote` oppure un link diretto con `competitionId`.
2. Il frontend verifica l'accesso pubblico tramite `POST /api/competitions/{id}/public-access`.
3. Dopo l'accesso carica competizione, partecipanti, criteri pubblici e sessioni di voto in parallelo.
4. Se non esiste una sessione aperta, mostra lo stato di attesa/chiusura e non rende inviabile il voto.
5. Con una sessione aperta rende l'interfaccia coerente con `single_choice`, `ranked_choice` o `criteria_rating`.
6. Dopo un invio riuscito sostituisce il form con lo stato di conferma.

La generazione e persistenza del token anonimo del votante resta invariata.

## Errori e accessibilità

- Errori di accesso o API vengono mostrati dentro la pagina pubblica con lo stato grafico dedicato e un'azione di riprova.
- I controlli mantengono label o nomi accessibili, focus visibile e uso da tastiera.
- La selezione non dipende soltanto dal colore: usa anche bordo, icona e stato ARIA.
- Testi e CTA rispettano un contrasto leggibile sul fondo scuro.
- La pagina resta utilizzabile da 320 px in su.

## Verifica

- Test minimo del riconoscimento della route `/vote` prima dell'implementazione del routing.
- Build TypeScript/Vite completa.
- Verifica dei tre metodi di voto e degli stati accesso, attesa, aperto, confermato, chiuso ed errore.
- Confronto visivo a viewport mobile e desktop con `immagine_reference.png` e con il mockup approvato della variante B.

## Fuori ambito

- Modifiche al backend o alle regole di voto.
- Upload di fotografie personalizzate dei partecipanti.
- Nuovo sistema di routing o librerie UI.
- Restyling delle aree admin, giudici e schermo pubblico.
