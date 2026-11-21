import { ChangeEvent } from "react";
import { Card, Form } from "react-bootstrap";
import { ImportType } from "../api-client";
import TapirButton from "../components/TapirButton";
export default function DataImportUploadCard({
  types,
  selected,
  setSelected,
  file,
  setFile,
  update,
  setUpdate,
  onSubmit,
  loading,
}: {
  types: ImportType[];
  selected: string[];
  setSelected: (v: string[]) => void;
  file?: File;
  setFile: (v?: File) => void;
  update: boolean;
  setUpdate: (v: boolean) => void;
  onSubmit: () => void;
  loading: boolean;
}) {
  const select = (event: ChangeEvent<HTMLInputElement>, key: string) =>
    setSelected(
      event.target.checked
        ? [...selected, key]
        : selected.filter((item) => item !== key),
    );
  return (
    <Card className="mb-3">
      <Card.Header>1. Datei hochladen</Card.Header>
      <Card.Body>
        <Form
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          <Form.Group className="mb-3">
            <Form.Label>Was wird übernommen?</Form.Label>
            {types.map((type) => (
              <Form.Check
                key={type.key}
                id={`data-import-type-${type.key}`}
                label={type.name}
                checked={selected.includes(type.key)}
                onChange={(event) => select(event, type.key)}
              />
            ))}
            <Form.Text>
              Eine Datei kann mehrere Typen gleichzeitig abdecken: jede
              nicht-leere Zeile wird dann für alle ausgewählten Typen verwendet,
              in dieser Reihenfolge: Mitglieder, Genossenschaftsanteile,
              Verträge.
            </Form.Text>
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>Datei</Form.Label>
            <Form.Control
              type="file"
              accept=".xlsx,.xlsm,.csv"
              onChange={(event) =>
                setFile((event.currentTarget as HTMLInputElement).files?.[0])
              }
            />
            <Form.Text>
              Excel (.xlsx) oder CSV. Die erste Zeile enthält die Spaltennamen,
              die erste Tabelle wird gelesen.
            </Form.Text>
          </Form.Group>
          <Form.Group>
            <Form.Check
              id="data-import-update-existing"
              label="Bestehende Datensätze aktualisieren"
              checked={update}
              onChange={(event) => setUpdate(event.target.checked)}
            />
            <Form.Text>
              Ohne Haken werden bereits vorhandene Mitglieder, Anteile und
              Verträge übersprungen.
            </Form.Text>
          </Form.Group>
          <TapirButton
            className="mt-3"
            variant="outline-primary"
            text="Prüfen"
            icon="fact_check"
            type="submit"
            loading={loading}
            disabled={!file || !selected.length}
          />
          {(!file || !selected.length) && (
            <Form.Text>
              {!selected.length && !file
                ? "Bitte mindestens einen Typ auswählen und eine Datei wählen."
                : !selected.length
                  ? "Bitte mindestens einen Typ auswählen."
                  : "Bitte eine Datei wählen."}
            </Form.Text>
          )}
        </Form>
      </Card.Body>
    </Card>
  );
}
