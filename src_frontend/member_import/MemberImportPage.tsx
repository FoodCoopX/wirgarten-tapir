import { FormEvent, useState } from "react";
import { Alert, Button, Card, Form, Table } from "react-bootstrap";
import { MemberImportApi, MemberImportResult } from "../api-client";
import TapirButton from "../components/TapirButton";
import TapirToastContainer from "../components/TapirToastContainer";
import { useApi } from "../hooks/useApi";
import { ToastData } from "../types/ToastData";
import { handleRequestError } from "../utils/handleRequestError";

export default function MemberImportPage({
  csrfToken,
  templateUrl,
}: {
  csrfToken: string;
  templateUrl: string;
}) {
  const api = useApi(MemberImportApi, csrfToken);
  const [file, setFile] = useState<File>();
  const [token, setToken] = useState<string>();
  const [result, setResult] = useState<MemberImportResult>();
  const [loading, setLoading] = useState<"preview" | "apply">();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function handleFileChange(selectedFile?: File) {
    setFile(selectedFile);
    setResult(undefined);
    setToken(undefined);
  }

  async function handlePreview(event: FormEvent) {
    event.preventDefault();
    if (!file || loading) return;
    setLoading("preview");
    setResult(undefined);
    setToken(undefined);
    try {
      const response = await api.memberImportPreview({ file });
      setResult(response.result);
      setToken(response.token ?? undefined);
    } catch (error) {
      handleRequestError(
        error,
        "Die Datei konnte nicht geprüft werden.",
        setToastDatas,
      );
    } finally {
      setLoading(undefined);
    }
  }

  async function handleApply() {
    if (!token || loading) return;
    setLoading("apply");
    try {
      setResult(
        await api.memberImportApply({ memberImportApplyRequest: { token } }),
      );
    } catch (error) {
      handleRequestError(
        error,
        "Der Import konnte nicht abgeschlossen werden.",
        setToastDatas,
      );
    } finally {
      setToken(undefined);
      setLoading(undefined);
    }
  }

  return (
    <div className="container py-3">
      <h1>Mitglieder importieren</h1>
      <p>
        Neue Mitglieder aus CSV oder Excel übernehmen. Bereits vorhandene
        Mitgliedsnummern werden übersprungen. Es werden keine Aktivierungsmails
        versendet.
      </p>
      <p>
        Abholorte und Vereinsmitgliedschaftstypen müssen vorher angelegt sein.
        Fehler bitte in der Datei korrigieren und die Datei erneut hochladen.
      </p>
      <Button href={templateUrl} variant="outline-secondary" className="mb-3">
        Vorlage herunterladen
      </Button>
      <Card className="mb-3">
        <Card.Body>
          <Form onSubmit={handlePreview}>
            <Form.Group controlId="member-import-file" className="mb-3">
              <Form.Label>Mitgliederdatei</Form.Label>
              <Form.Control
                type="file"
                accept=".csv,.xlsx"
                disabled={!!loading}
                onChange={(event) =>
                  handleFileChange(
                    (event.currentTarget as HTMLInputElement).files?.[0],
                  )
                }
              />
              <Form.Text>
                CSV oder Excel (.xlsx), mit den Spaltennamen aus der Vorlage.
                Bei Excel wird das erste Tabellenblatt gelesen.
              </Form.Text>
            </Form.Group>
            <TapirButton
              type="submit"
              variant="outline-primary"
              text="Datei prüfen"
              disabled={!file || !!loading}
              loading={loading === "preview"}
            />
          </Form>
        </Card.Body>
      </Card>
      {result && (
        <>
          {result.applied ? (
            <output className="alert alert-success d-block">
              Import abgeschlossen.
            </output>
          ) : (
            <p>Prüfergebnis. Es wurden keine Daten gespeichert.</p>
          )}
          {result.errors.map((error) => (
            <Alert key={error} variant="danger">
              {error}
            </Alert>
          ))}
          {result.rows.length > 0 && (
            <Table responsive>
              <thead>
                <tr>
                  <th scope="col">Zeile</th>
                  <th scope="col">Ergebnis</th>
                  <th scope="col">Hinweis</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row) => (
                  <tr
                    key={row.line}
                    className={row.error ? "table-danger" : undefined}
                  >
                    <td>{row.line}</td>
                    <td>{row.status}</td>
                    <td>{row.error}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
          {token && result.canApply ? (
            <TapirButton
              variant="primary"
              text="Mitglieder importieren"
              onClick={handleApply}
              loading={loading === "apply"}
              disabled={!!loading}
            />
          ) : !result.applied && !result.canApply ? (
            <p>
              Es wurde nichts übernommen. Bitte die Fehler korrigieren und
              erneut prüfen.
            </p>
          ) : null}
        </>
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
}
