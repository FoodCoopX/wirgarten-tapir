import { Card, Form, Table } from "react-bootstrap";
import { Column, SemanticField, UploadResponse } from "../api-client";
import TapirButton from "../components/TapirButton";
import {
  defaultPickupTarget,
  pickupColumnValues,
} from "./pickupLocationMapping";
export default function DataImportMappingCard({
  upload,
  mapping,
  setMapping,
  defaults,
  setDefaults,
  options,
  setOptions,
  pickupMapping,
  setPickupMapping,
  createMissingPickupLocations,
  setCreateMissingPickupLocations,
  errors,
  onSubmit,
  loading,
  onBack,
}: {
  upload: UploadResponse;
  mapping: Record<number, string>;
  setMapping: (v: Record<number, string>) => void;
  defaults: Record<string, string>;
  setDefaults: (v: Record<string, string>) => void;
  options: {
    accountOwnerFromName: boolean;
    sepaConsentFromContractStart: boolean;
  };
  setOptions: (v: {
    accountOwnerFromName: boolean;
    sepaConsentFromContractStart: boolean;
  }) => void;
  pickupMapping: Record<string, string>;
  setPickupMapping: (v: Record<string, string>) => void;
  createMissingPickupLocations: boolean;
  setCreateMissingPickupLocations: (v: boolean) => void;
  errors: string[];
  onSubmit: () => void;
  loading: boolean;
  onBack: () => void;
}) {
  const used = new Set(Object.values(mapping).filter(Boolean));
  const hasProductColumn = upload.semanticFields.some(
    (field) =>
      field.kind === "quantity" && Object.values(mapping).includes(field.key),
  );
  const contractStartAvailable =
    Object.values(mapping).includes("subscriptions:Vertragsbeginn") ||
    !!defaults["subscriptions:Vertragsbeginn"]?.trim();
  const missingFields = upload.semanticFields.filter(
    (field) =>
      field.required &&
      !(field.requiredUnlessProductColumns && hasProductColumn) &&
      !(
        field.key === "members:consent_sepa" &&
        options.sepaConsentFromContractStart &&
        contractStartAvailable
      ) &&
      !Object.values(mapping).includes(field.key) &&
      !(field.allowsDefault && !!defaults[field.key]?.trim()),
  );
  const required = missingFields.length === 0;
  const missingWithDefaults = missingFields.filter(
    (field) => field.allowsDefault,
  );
  const missingWithoutDefaults = missingFields.filter(
    (field) => !field.allowsDefault,
  );
  const missingHintParts = [
    missingWithDefaults.length > 0
      ? `${missingWithDefaults.map((field) => field.label).join(", ")} – einer Spalte zuordnen oder Standardwert setzen`
      : "",
    missingWithoutDefaults.length > 0
      ? `${missingWithoutDefaults.map((field) => field.label).join(", ")} – einer Spalte zuordnen`
      : "",
  ].filter(Boolean);
  const headerByKey = Object.fromEntries(
    upload.columns
      .filter((column) => mapping[column.index])
      .map((column) => [mapping[column.index], column.header]),
  );
  const inputType = (kind: string) =>
    kind === "date" || kind === "datetime"
      ? "date"
      : kind === "int" || kind === "decimal"
        ? "number"
        : "text";
  return (
    <Card className="mb-3">
      <Card.Header>2. Spalten zuordnen</Card.Header>
      <Card.Body>
        <p>
          Jede Spalte der Datei kann einem Zielfeld zugeordnet werden, oder
          „Nicht importieren“. Felder mit * sind für die ausgewählten Typen
          Pflicht und müssen alle zugeordnet sein, bevor geprüft werden kann.
          Ein Ziel kann höchstens einer Spalte zugeordnet werden. Zahl = Menge
          bei Produktspalten, Kommazahlen sind nicht möglich. PZ/PA in Nr. führt
          zu einer automatischen Nummer und Probezeit.
        </p>
        {errors.map((error) => (
          <div className="alert alert-danger" key={error}>
            {error}
          </div>
        ))}
        <div className="table-responsive" style={{ maxHeight: "70vh" }}>
          <Table size="sm">
            <thead className="sticky-top bg-white">
              <tr>
                {upload.columns.map((column: Column) => (
                  <th key={column.index} style={{ verticalAlign: "top" }}>
                    <div className="text-nowrap">{column.header}</div>
                    <Form.Select
                      value={mapping[column.index] ?? ""}
                      onChange={(event) =>
                        setMapping({
                          ...mapping,
                          [column.index]: event.target.value,
                        })
                      }
                    >
                      <option value="">Nicht importieren</option>
                      {upload.semanticFields.map((field: SemanticField) => (
                        <option
                          key={field.key}
                          value={field.key}
                          disabled={
                            used.has(field.key) &&
                            mapping[column.index] !== field.key
                          }
                        >
                          {field.label}
                          {field.required ? " *" : ""}
                          {headerByKey[field.key]
                            ? ` [${headerByKey[field.key]}]`
                            : ""}
                        </option>
                      ))}
                    </Form.Select>
                    {(() => {
                      const field = upload.semanticFields.find(
                        (item) => item.key === mapping[column.index],
                      );
                      if (!field?.allowsDefault) {
                        if (field?.key === "members:Kontoinhaber")
                          return (
                            <Form.Check
                              className="mt-1"
                              label="Wenn leer: Vor- und Nachname verwenden"
                              checked={options.accountOwnerFromName}
                              onChange={(e) =>
                                setOptions({
                                  ...options,
                                  accountOwnerFromName: e.target.checked,
                                })
                              }
                            />
                          );
                        if (
                          field?.key === "members:consent_sepa" &&
                          upload.semanticFields.some((f) =>
                            f.key.startsWith("subscriptions:"),
                          )
                        )
                          return (
                            <Form.Check
                              className="mt-1"
                              label="Wenn leer: Vertragsbeginn verwenden"
                              checked={options.sepaConsentFromContractStart}
                              onChange={(e) =>
                                setOptions({
                                  ...options,
                                  sepaConsentFromContractStart:
                                    e.target.checked,
                                })
                              }
                            />
                          );
                        return (
                          <Form.Control
                            className="mt-1 invisible"
                            size="sm"
                            disabled
                            aria-hidden
                          />
                        );
                      }
                      return (
                        <Form.Control
                          className="mt-1"
                          size="sm"
                          type={inputType(field.kind)}
                          placeholder="Standardwert für leere Zellen"
                          value={defaults[field.key] ?? ""}
                          onChange={(event) =>
                            setDefaults({
                              ...defaults,
                              [field.key]: event.target.value,
                            })
                          }
                        />
                      );
                    })()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {upload.previewRows.map((row, index) => (
                <tr key={index}>
                  {row.map((value, cell) => (
                    <td key={cell}>{value}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
        {(() => {
          const distinct = pickupColumnValues(upload, mapping);
          if (!distinct) return null;
          if (distinct.capped) {
            return (
              <div className="alert alert-warning mt-3">
                Für Abholorte mit mehr als 100 verschiedenen Werten ist keine
                Zuordnungsliste verfügbar.
              </div>
            );
          }
          const targetFor = (
            value: string,
            allowCreate = createMissingPickupLocations,
          ) => defaultPickupTarget(value, upload.pickupLocations, allowCreate);
          return (
            <>
              <h6 className="mt-3">Abholorte zuordnen</h6>
              <Form.Check
                type="checkbox"
                label="Fehlende Abholorte anlegen"
                checked={createMissingPickupLocations}
                onChange={(event) => {
                  const checked = event.target.checked;
                  setCreateMissingPickupLocations(checked);
                  const next = { ...pickupMapping };
                  distinct.values.forEach(({ value }) => {
                    if (
                      !next[value] ||
                      next[value] === "create" ||
                      next[value] === "skip"
                    )
                      next[value] = targetFor(value, checked);
                  });
                  setPickupMapping(next);
                }}
              />
              <p className="text-muted small mt-2">
                Neu angelegte Abholorte erhalten nur den Namen und werden allen
                Produkttypen mit unbegrenzter Kapazität zugeordnet. Adresse und
                Kapazitäten können anschließend in der Abholortverwaltung
                gepflegt werden.
              </p>
              <Table size="sm">
                <thead>
                  <tr>
                    <th>Wert in der Datei</th>
                    <th>Anzahl Zeilen</th>
                    <th>Zuordnung</th>
                  </tr>
                </thead>
                <tbody>
                  {distinct.values.map(({ value, count }) => (
                    <tr key={value}>
                      <td>{value}</td>
                      <td>{count}</td>
                      <td>
                        <Form.Select
                          value={pickupMapping[value] ?? targetFor(value)}
                          onChange={(event) =>
                            setPickupMapping({
                              ...pickupMapping,
                              [value]: event.target.value,
                            })
                          }
                        >
                          {upload.pickupLocations.map((location) => (
                            <option
                              key={location.id}
                              value={`existing:${location.id}`}
                            >
                              {location.name}
                            </option>
                          ))}
                          <option value="create">Neu anlegen</option>
                          <option value="skip">Nicht zuordnen</option>
                        </Form.Select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </>
          );
        })()}
        <h6 className="mt-3">Felder, die nicht in der Datei vorkommen</h6>
        <div className="row g-2">
          {upload.semanticFields
            .filter(
              (field) =>
                (field.allowsDefault || field.required) &&
                !Object.values(mapping).includes(field.key),
            )
            .map((field) => (
              <div className="col-md-4" key={field.key}>
                <Form.Label>
                  {field.label}
                  {field.required ? " *" : ""}
                </Form.Label>
                {field.allowsDefault ? (
                  <Form.Control
                    type={inputType(field.kind)}
                    value={defaults[field.key] ?? ""}
                    className={
                      field.required && !defaults[field.key]?.trim()
                        ? "is-invalid"
                        : ""
                    }
                    placeholder="Standardwert"
                    onChange={(event) =>
                      setDefaults({
                        ...defaults,
                        [field.key]: event.target.value,
                      })
                    }
                  />
                ) : field.key === "members:Kontoinhaber" ? (
                  <Form.Check
                    label="Wenn leer: Vor- und Nachname verwenden"
                    checked={options.accountOwnerFromName}
                    onChange={(e) =>
                      setOptions({
                        ...options,
                        accountOwnerFromName: e.target.checked,
                      })
                    }
                  />
                ) : field.key === "members:consent_sepa" &&
                  upload.semanticFields.some((f) =>
                    f.key.startsWith("subscriptions:"),
                  ) ? (
                  <Form.Check
                    label="Wenn leer: Vertragsbeginn verwenden"
                    checked={options.sepaConsentFromContractStart}
                    onChange={(e) =>
                      setOptions({
                        ...options,
                        sepaConsentFromContractStart: e.target.checked,
                      })
                    }
                  />
                ) : (
                  <div className="text-muted small">Einer Spalte zuordnen</div>
                )}
              </div>
            ))}
        </div>
        <p className="text-muted">
          {upload.previewRows.length < upload.totalRows
            ? `Zeigt die ersten ${upload.previewRows.length} von ${upload.totalRows} Zeilen`
            : `Zeigt ${upload.totalRows} Zeilen`}
        </p>
        {!required && (
          <div className="text-danger small mb-2" role="status">
            Noch offen: {missingHintParts.join("; ")}
          </div>
        )}
        <div className="d-flex gap-2">
          <TapirButton
            variant="outline-secondary"
            text="Zurück"
            icon="arrow_back"
            onClick={onBack}
          />
          <TapirButton
            variant="outline-primary"
            text="Prüfen"
            icon="fact_check"
            onClick={onSubmit}
            loading={loading}
            disabled={!required}
          />
        </div>
      </Card.Body>
    </Card>
  );
}
