import React, { useEffect, useState } from "react";
import { Card, Col, Row } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  CsvExportModel,
  ExportSegment,
  GenericExportsApi,
} from "../api-client";
import CsvExportTable from "./CsvExportTable.tsx";
import CsvExportModal from "./CsvExportModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import CsvExportBuildModal from "./CsvExportBuildModal.tsx";
import { handleRequestError } from "../utils/handleRequestError.ts";

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

  useEffect(() => {
    setSegmentsLoading(true);
    api
      .genericExportsExportSegmentsList()
      .then(setSegments)
      .catch(handleRequestError)
      .finally(() => setSegmentsLoading(false));

    loadExports();
  }, []);

  function loadExports() {
    setExportsLoading(true);
    api
      .genericExportsCsvExportsList()
      .then(setExports)
      .catch(handleRequestError)
      .finally(() => setExportsLoading(false));
  }

  function deleteExport(exp: CsvExportModel) {
    api
      .genericExportsCsvExportsDestroy({ id: exp.id! })
      .then(() => loadExports())
      .catch(handleRequestError)
      .finally(() => setExportSelectedForDeletion(undefined));
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
        />
      )}
    </>
  );
};

export default CsvExportEditor;
