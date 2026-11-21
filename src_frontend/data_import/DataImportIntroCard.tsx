import { Card } from "react-bootstrap";
import { ImportType } from "../api-client";
import TapirButton from "../components/TapirButton";

export default function DataImportIntroCard({
  types,
}: {
  types: ImportType[];
}) {
  return (
    <Card className="mb-3">
      <Card.Header>Datenübernahme</Card.Header>
      <Card.Body>
        <p>
          Übernimmt den Bestand aus einer Excel- oder CSV-Datei für die
          ausgewählten Typen. Eine Datei kann mehrere Typen gleichzeitig
          abdecken: jede nicht-leere Zeile wird für alle ausgewählten Typen
          verwendet, in dieser Reihenfolge: <strong>Mitglieder</strong>, dann{" "}
          <strong>Genossenschaftsanteile</strong>, dann{" "}
          <strong>Verträge</strong>. Abholorte, Produkttypen, Produkte und
          Vertragsperioden müssen vorher in Tapir angelegt sein, die Tabelle
          nennt sie mit demselben Namen.
        </p>
        <p className="mb-2">
          Ablauf: erst die Spalten der Datei den Zielfeldern zuordnen, dann wird
          jede Zeile geprüft, dann können nur die gültigen und ausgewählten
          Zeilen übernommen werden. Vorlagen mit allen Spalten (Pflichtspalten
          fett) und einer Beispielzeile, falls lieber mit festen Spaltennamen
          gearbeitet wird:
        </p>
        <div className="d-flex flex-wrap gap-2">
          {types.map((type) => (
            <TapirButton
              key={type.key}
              variant="outline-secondary"
              text={`Vorlage ${type.name}`}
              icon="download"
              onClick={() => {
                window.location.href = type.templateUrl;
              }}
            />
          ))}
        </div>
      </Card.Body>
    </Card>
  );
}
