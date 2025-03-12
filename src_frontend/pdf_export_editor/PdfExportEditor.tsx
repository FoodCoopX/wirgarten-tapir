import React, { useEffect, useState } from "react";
import { Card, Col, Row } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  ExportSegment,
  GenericExportsApi,
  PdfExportModel,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import PdfExportTable from "./PdfExportTable.tsx";
import PdfExportModal from "./PdfExportModal.tsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import PdfExportBuildModal from "./PdfExportBuildModal.tsx";

interface PdfExportEditorProps {
  csrfToken: string;
}

const PdfExportEditor: React.FC<PdfExportEditorProps> = ({ csrfToken }) => {
  const api = useApi(GenericExportsApi, csrfToken);
  const [segments, setSegments] = useState<ExportSegment[]>([]);
  const [segmentsLoading, setSegmentsLoading] = useState(false);
  const [exports, setExports] = useState<PdfExportModel[]>([]);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [showPdfExportModal, setShowPdfExportModal] = useState(false);
  const [exportSelectedForDeletion, setExportSelectedForDeletion] =
    useState<PdfExportModel>();
  const [exportSelectedForEdition, setExportSelectedForEdition] =
    useState<PdfExportModel>();
  const [exportSelectedForBuild, setExportSelectedForBuild] =
    useState<PdfExportModel>();

  useEffect(() => {
    setSegmentsLoading(true);
    api
      .genericExportsExportSegmentsList()
      .then(setSegments)
      .catch(alert)
      .finally(() => setSegmentsLoading(false));

    loadExports();
  }, []);

  function loadExports() {
    setExportsLoading(true);
    api
      .genericExportsPdfExportsList()
      .then(setExports)
      .catch(alert)
      .finally(() => setExportsLoading(false));
  }

  function deleteExport(exp: PdfExportModel) {
    api
      .genericExportsPdfExportsDestroy({ id: exp.id! })
      .then(() => loadExports())
      .catch(alert)
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
                <h5 className={"mb-0"}>PDF-Export Editor</h5>
                <TapirButton
                  variant={"outline-primary"}
                  text={"Neues Export erzeugen"}
                  icon={"add_circle"}
                  onClick={() => setShowPdfExportModal(true)}
                  disabled={segmentsLoading}
                />
              </div>
            </Card.Header>
            <Card.Body>
              <PdfExportTable
                exports={exports}
                loading={exportsLoading}
                onExportEdit={(exp) => {
                  setExportSelectedForEdition(exp);
                  setShowPdfExportModal(true);
                }}
                segments={segmentsLoading ? [] : segments}
                onExportDeleteClicked={(exp) => {
                  setExportSelectedForDeletion(exp);
                }}
                onExportBuildClicked={(exp) => {
                  setExportSelectedForBuild(exp);
                }}
              />
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <PdfExportModal
        show={showPdfExportModal}
        onHide={() => {
          setShowPdfExportModal(false);
          setExportSelectedForEdition(undefined);
        }}
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
        <PdfExportBuildModal
          exportToBuild={exportSelectedForBuild}
          show={true}
          csrfToken={csrfToken}
          onHide={() => setExportSelectedForBuild(undefined)}
        />
      )}
    </>
  );
};

export default PdfExportEditor;
