import React from "react";
import { Badge, Card, Form, Table } from "react-bootstrap";
import { ReviewResponse } from "../api-client";
import TapirButton from "../components/TapirButton";
export default function DataImportReviewCard({
  review,
  selected,
  setSelected,
  onApply,
  onBack,
  loading,
  updateExisting,
  setUpdateExisting,
  onRecheck,
  onEdit,
}: {
  review: ReviewResponse;
  selected: number[];
  setSelected: (v: number[]) => void;
  onApply: () => void;
  onBack: () => void;
  loading: boolean;
  updateExisting: boolean;
  setUpdateExisting: (v: boolean) => void;
  onRecheck: (v: boolean) => void;
  onEdit: (rowIndex: number, header: string, value: string) => Promise<void>;
}) {
  const [hideUnchanged, setHideUnchanged] = React.useState(true);
  const [editing, setEditing] = React.useState<{
    row: number;
    column: number;
  }>();
  const [editValue, setEditValue] = React.useState("");
  const counts = review.statusCounts ?? {};
  const visible = review.rows.filter(
    (row) =>
      !(
        hideUnchanged &&
        (row.status === "unchanged" ||
          (!updateExisting && row.status === "existing"))
      ),
  );
  const selectable = visible
    .filter(
      (row) => row.valid && (row.status === "new" || row.status === "changed"),
    )
    .map((row) => row.index);
  const all =
    selectable.length > 0 &&
    selectable.every((index) => selected.includes(index));
  return (
    <Card className="mb-3">
      <Card.Header>3. Prüfung</Card.Header>
      <Card.Body>
        <div className="d-flex flex-wrap gap-2 mb-2">
          <Badge bg="success">{counts.new ?? 0} neu</Badge>
          <Badge bg="primary">{counts.changed ?? 0} geändert</Badge>
          <Badge bg="secondary">
            {counts.unchanged ?? 0} unverändert
            {hideUnchanged ? " (ausgeblendet)" : ""}
          </Badge>
          <Badge bg="dark">{counts.existing ?? 0} vorhanden</Badge>
          <Badge bg="danger">
            {counts.invalid ?? review.invalidCount} ungültig
          </Badge>
        </div>
        <div className="d-flex gap-4 mb-2">
          <Form.Check
            type="checkbox"
            label="Unveränderte Datensätze ausblenden"
            checked={hideUnchanged}
            onChange={(e) => setHideUnchanged(e.target.checked)}
          />
          <Form.Check
            type="checkbox"
            label="Bestehende Datensätze aktualisieren"
            checked={updateExisting}
            onChange={(e) => {
              setUpdateExisting(e.target.checked);
              onRecheck(e.target.checked);
            }}
          />
        </div>
        <p className="mt-3">
          Grün: Zelle gültig. Rot: Zelle fehlt (Pflichtfeld) oder hat ein
          ungültiges Format. Gelb: optionales Feld in dieser Zeile leer, obwohl
          die Spalte sonst Werte hat. Orange: Wert ungültig, die Zeile wird ohne
          diesen Wert übernommen. Kursiv und grau hinterlegt: Standardwert
          eingesetzt. Durchgestrichen darüber: bisheriger Wert eines bestehenden
          Mitglieds. Ausgegraute Zeilen: Datensatz besteht bereits und wird
          nicht geändert. Grau: nicht zugeordnet oder optionales Feld, dessen
          Spalte durchgehend leer ist. Nur ausgewählte, gültige Zeilen werden
          übernommen; schlägt eine ausgewählte Zeile beim Übernehmen unerwartet
          fehl, wird alles zurückgerollt. Bearbeitbare Zellen lassen sich per
          Klick korrigieren; ein blauer Rand und ✎ markieren korrigierte Werte,
          beim Darüberfahren erscheint der ursprüngliche Wert.
        </p>
        <Form.Check
          className="mb-2"
          label="Alle gültigen auswählen"
          checked={all}
          onChange={(e) => setSelected(e.target.checked ? selectable : [])}
        />
        <div className="table-responsive" style={{ maxHeight: "70vh" }}>
          <Table size="sm">
            <thead className="sticky-top bg-white">
              <tr>
                <th />
                <th>Zeile</th>
                {review.headers.map((h) => (
                  <th key={h}>{h}</th>
                ))}
                <th style={{ minWidth: "30rem" }}>Meldung</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr
                  key={row.index}
                  className={
                    row.status === "unchanged" || row.status === "existing"
                      ? "opacity-50"
                      : undefined
                  }
                >
                  <td>
                    <Form.Check
                      disabled={
                        !row.valid ||
                        row.status === "unchanged" ||
                        row.status === "existing"
                      }
                      checked={selected.includes(row.index)}
                      onChange={(e) =>
                        setSelected(
                          e.target.checked
                            ? [...selected, row.index]
                            : selected.filter((i) => i !== row.index),
                        )
                      }
                    />
                  </td>
                  <td>{row.line}</td>
                  {row.cells.map((cell, i) => {
                    const isEditing =
                      editing?.row === row.index && editing.column === i;
                    const save = (value: string) => {
                      if (!isEditing) return;
                      setEditing(undefined);
                      if (value !== String(cell.value ?? "")) {
                        void onEdit(row.index, review.headers[i], value);
                      }
                    };
                    return (
                      <td
                        key={i}
                        title={
                          cell.edited
                            ? `Ursprünglich: ${cell.originalValue ?? ""}`
                            : undefined
                        }
                        onClick={() => {
                          if (cell.editable && !isEditing) {
                            setEditing({ row: row.index, column: i });
                            setEditValue(String(cell.value ?? ""));
                          }
                        }}
                        style={{
                          backgroundColor: (
                            {
                              valid: "#d1e7dd",
                              invalid: "#f8d7da",
                              warn: "#ffe69c",
                              dropped: "#ffd8a8",
                              neutral: "transparent",
                              default: "#e9ecef",
                            } as Record<string, string>
                          )[cell.state],
                          borderLeft: cell.edited
                            ? "3px solid #0d6efd"
                            : undefined,
                          cursor: cell.editable ? "text" : undefined,
                        }}
                      >
                        {isEditing ? (
                          <>
                            <Form.Control
                              size="sm"
                              autoFocus
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => save(editValue)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") save(editValue);
                                if (e.key === "Escape") setEditing(undefined);
                              }}
                            />
                            {cell.edited && (
                              <button
                                type="button"
                                className="btn btn-link btn-sm p-0"
                                onMouseDown={(e) => e.preventDefault()}
                                onClick={() => save(cell.originalValue ?? "")}
                              >
                                Zurücksetzen
                              </button>
                            )}
                          </>
                        ) : (
                          <span
                            className={
                              cell.state === "default"
                                ? "fst-italic"
                                : undefined
                            }
                          >
                            {cell.oldValue !== undefined &&
                            cell.oldValue !== cell.value ? (
                              <>
                                <span className="text-muted text-decoration-line-through">
                                  {cell.oldValue || "(leer)"}
                                </span>
                                <br />
                              </>
                            ) : null}
                            {cell.value}
                            {cell.edited ? " ✎" : ""}
                          </span>
                        )}
                      </td>
                    );
                  })}
                  <td>{row.messages.join(" ")}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
        <div className="d-flex gap-2">
          <TapirButton
            variant="outline-secondary"
            text="Zurück"
            icon="arrow_back"
            onClick={onBack}
          />
          <TapirButton
            variant="primary"
            text="Übernehmen"
            icon="check"
            onClick={onApply}
            loading={loading}
            disabled={!selected.length}
          />
        </div>
      </Card.Body>
    </Card>
  );
}
