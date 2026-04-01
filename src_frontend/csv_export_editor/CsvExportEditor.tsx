import React, { useEffect, useState } from "react";
import { Card, Col, Row } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  AutomatedExportCycleEnum,
  CsvExportModel,
  ExportSegment,
  GenericExportsApi,
  LocaleEnum,
} from "../api-client";
import CsvExportTable from "./CsvExportTable.tsx";
import CsvExportModal from "./CsvExportModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import CsvExportBuildModal from "./CsvExportBuildModal.tsx";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { ToastData } from "../types/ToastData.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";

interface CsvExportEditorProps {
  csrfToken: string;
}

const CsvExportEditor: React.FC<CsvExportEditorProps> = ({ csrfToken }) => {
  const api = useApi(GenericExportsApi, csrfToken);
  const [segments, setSegments] = useState<ExportSegment[]>([]);
  const [segmentsLoading, setSegmentsLoading] = useState(false);
  const [exports, setExports] = useState<CsvExportModel[]>([]);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [showCsvExportModal, setShowCsvExportModal] = useState(false);
  const [exportSelectedForDeletion, setExportSelectedForDeletion] =
    useState<CsvExportModel>();
  const [exportSelectedForEdition, setExportSelectedForEdition] =
    useState<CsvExportModel>();
  const [exportSelectedForBuild, setExportSelectedForBuild] =
    useState<CsvExportModel>();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    setSegmentsLoading(true);
    api
      .genericExportsExportSegmentsList()
      .then(setSegments)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Segmente",
          setToastDatas,
        ),
      )
      .finally(() => setSegmentsLoading(false));

    loadExports();
  }, []);

  function loadExports() {
    setExportsLoading(true);
    api
      .genericExportsCsvExportsList()
      .then(setExports)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Exports",
          setToastDatas,
        ),
      )
      .finally(() => setExportsLoading(false));
  }

  function deleteExport(exp: CsvExportModel) {
    api
      .genericExportsCsvExportsDestroy({ id: exp.id! })
      .then(() => loadExports())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Löschen des Exports",
          setToastDatas,
        ),
      )
      .finally(() => setExportSelectedForDeletion(undefined));
  }

  function promptNewGenGExport() {
    setExportSelectedForEdition({
      exportSegmentId: "members.all",
      name: "GenG. Mitgliederliste",
      separator: ",",
      fileName: "GenG. Mitgliederliste.csv",
      columnIds: [
        "member_number",
        // https://www.gesetze-im-internet.de/geng/__30.html
        // (2) In die Mitgliederliste ist jedes Mitglied der Genossenschaft mit folgenden Angaben einzutragen:

        // 1. Familienname, Vornamen und Anschrift, bei juristischen Personen und Personenhandelsgesellschaften Firma und Anschrift, bei anderen Personenvereinigungen Bezeichnung und Anschrift der Vereinigung oder Familiennamen, Vornamen und Anschriften ihrer Mitglieder,
        "member_last_name",
        "member_first_name",
        "member_full_address",
        // "member_phone_number",
        // "member_email_address",

        // 2. Zahl der von ihm übernommenen weiteren Geschäftsanteile,
        "member_admission_date",
        "member_share_quantity",
        // 3. Ausscheiden aus der Genossenschaft.
        // Der Zeitpunkt, zu dem der Beitritt, eine Veränderung der Zahl weiterer Geschäftsanteile oder das Ausscheiden wirksam wird oder geworden ist, ist anzugeben.
        "member_share_history",
        "member_termination_date",
      ],
      customColumnNames: [
        "Mitgliedsnummer",
        // 1.
        "Familienname",
        "Vorname(n)",
        "Anschrift",
        // 2.
        "Beitrittsdatum",
        "Anzahl Anteile",
        // 3.
        "Anteilshistorie",
        "Austrittsdatum",
      ],
      automatedExportCycle: AutomatedExportCycleEnum.Never,
      automatedExportDay: 1,
      automatedExportHour: "12:00",
      locale: LocaleEnum.DeDeUtf8,
    });
    setShowCsvExportModal(true);
  }

  return (
    <>
      <Row className={"mt-4"}>
        <Col>
          <Card>
            <Card.Header>
              <div
                className={
                  "d-flex justify-content-between align-items-center mb-0"
                }
              >
                <h5 className={"mb-0"}>CSV-Export Editor</h5>
                <TapirButton
                  variant={"outline-primary"}
                  text={"GenG. Mitgliederliste erzeugen"}
                  icon={"add_circle"}
                  onClick={promptNewGenGExport}
                  disabled={segmentsLoading}
                />
                <TapirButton
                  variant={"outline-primary"}
                  text={"Neuen Export erzeugen"}
                  icon={"add_circle"}
                  onClick={() => {
                    setExportSelectedForEdition(undefined);
                    setShowCsvExportModal(true);
                  }}
                  disabled={segmentsLoading}
                />
              </div>
            </Card.Header>
            <Card.Body>
              <CsvExportTable
                exports={exports}
                loading={exportsLoading}
                onExportEdit={(exp) => {
                  setExportSelectedForEdition(exp);
                  setShowCsvExportModal(true);
                }}
                segments={segmentsLoading ? [] : segments}
                onExportDeleteClicked={setExportSelectedForDeletion}
                onExportBuildClicked={setExportSelectedForBuild}
              />
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <CsvExportModal
        show={showCsvExportModal}
        onHide={() => setShowCsvExportModal(false)}
        segments={segments}
        loadExports={loadExports}
        csrfToken={csrfToken}
        exportToEdit={exportSelectedForEdition}
        setToastDatas={setToastDatas}
      />
      {exportSelectedForDeletion && (
        <ConfirmDeleteModal
          open={true}
          message={
            'Export "' + exportSelectedForDeletion.name + '" wirklich löschen?'
          }
          onConfirm={() => deleteExport(exportSelectedForDeletion)}
          onCancel={() => setExportSelectedForDeletion(undefined)}
        />
      )}
      {exportSelectedForBuild && (
        <CsvExportBuildModal
          exportToBuild={exportSelectedForBuild}
          show={true}
          csrfToken={csrfToken}
          onHide={() => setExportSelectedForBuild(undefined)}
          setToastDatas={setToastDatas}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default CsvExportEditor;
