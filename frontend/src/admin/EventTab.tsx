// frontend/src/admin/EventTab.tsx
import type { EventRead, EventStatus } from "./types";
import { Panel, Form, List, Badge } from "./components";

type Props = {
  events: EventRead[];
  selectedEventId: string;
  onSelect: (id: string) => void;
  onDelete: (event: EventRead) => void;
  onCreate: (form: HTMLFormElement) => Promise<void>;
};

const eventStatusLabels: Record<EventStatus, string> = {
  draft: "draft",
  live: "live",
  closed: "chiuso",
  archived: "archiviato",
};

export function EventTab({
  events,
  selectedEventId,
  onSelect,
  onDelete,
  onCreate,
}: Props) {
  return (
    <Panel title="Eventi">
      <Form submitLabel="Crea evento" onSubmit={onCreate}>
        <input name="name" placeholder="Nome evento" required />
        <input name="description" placeholder="Descrizione" />
      </Form>
      <List>
        {events.map((event) => (
          <div
            className={event.id === selectedEventId ? "row active event-row" : "row event-row"}
            key={event.id}
          >
            <button
              className="event-select"
              onClick={() => onSelect(event.id)}
              type="button"
            >
              <span>{event.name}</span>
              <Badge>{eventStatusLabels[event.status] || event.status}</Badge>
            </button>
            <button
              className="danger-button"
              type="button"
              onClick={() => onDelete(event)}
            >
              Elimina
            </button>
          </div>
        ))}
      </List>
    </Panel>
  );
}
