# Manual ranking and podium reveal

## Goal

Give the event administrator manual control over the reveal timing for both the full
ranking and the final podium. Positions are revealed cumulatively from last to first.

## Existing system

`ScreenState.payload_json.reveal_upto` already stores a reveal counter and is persisted
and broadcast through the existing screen-state API and WebSocket. The ranking view uses
the counter only partially; a value of zero currently displays the complete ranking. The
podium ignores the counter and displays every podium position immediately. The existing
admin control advances by locating and submitting a form through DOM queries.

## State model

Continue using `payload_json.reveal_upto` as the number of positions currently visible.
No database migration or new API endpoint is required.

- The minimum value is `0`.
- For `reveal_ranking`, the maximum is the number of ranked results.
- For `show_podium` and `show_final_winners`, the maximum is the smaller of three and the
  number of ranked results.
- Values received outside the valid range are clamped before rendering or advancing.

Changing to a reveal mode starts from the counter submitted by the admin. The normal
workflow resets it to zero before beginning a new reveal.

## Reveal order

### Full ranking

At zero, no ranked participant is visible. Each forward action adds the next position in
this sequence: `N, N-1, ..., 2, 1`. Previously revealed positions remain visible.

### Podium

At zero, no podium card is visible. Forward actions reveal third, second, then first.
If fewer than three results exist, the sequence starts from the lowest available podium
position and still ends with first. Revealed cards retain their final podium placement.

## Admin controls

For ranking and podium reveal modes, the screen administration panel displays:

- `Azzera`, setting the counter to zero;
- `Indietro`, decrementing the counter by one;
- `Rivela prossima`, incrementing the counter by one;
- progress text showing visible positions, total positions, and the next rank to reveal.

Buttons are disabled at their respective boundaries and while an update is in flight.
Controls update `ScreenState` through a dedicated React action using the existing `PUT
/api/events/{event_id}/screen-state` endpoint. They do not query or mutate form elements
directly. Successful updates refresh admin state; the backend broadcast updates the public
screen immediately.

## Public screen behavior

The public screen derives the visible result subset from the screen mode, the clamped
counter, and the ordered results. A zero counter renders an explicit waiting state instead
of leaking unrevealed results. Ranking and podium use the same reveal-progress semantics,
while keeping their distinct layouts.

No automatic timer is introduced. Timing remains entirely under administrator control.

## Error handling

Failed updates leave the last persisted reveal state unchanged and surface the existing
admin error message. Boundary actions are prevented client-side; rendering remains safe if
an old or malformed payload contains a negative or oversized counter.

## Testing

Pure reveal helpers will be covered with frontend unit tests for:

- zero visible results;
- cumulative last-to-first ranking order;
- podium order `3, 2, 1`;
- fewer than three podium results;
- previous and reset behavior through counter changes;
- negative and oversized counter clamping;
- calculation of the next rank and completion state.

Existing backend screen-state and WebSocket tests remain valid because the API contract is
unchanged. Frontend build and the complete relevant test suite must pass before completion.
