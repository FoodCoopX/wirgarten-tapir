import React, { useEffect, useState } from "react";
import { Card, Col, Row } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  CsvExportModel,
  ExportSegment,
  GenericExportsApi,
} from "../api-client";
import CsvExportTable from "./CsvExportTable.tsx";
import CsvExportCreateModal from "./CsvExportCreateModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";

interface CsvExportEditorProps {
  csrfToken: string;
}

const CsvExportEditor: React.FC<CsvExportEditorProps> = ({ csrfToken }) => {
  const api = useApi(GenericExportsApi, csrfToken);
  const [segments, setSegments] = useState<ExportSegment[]>([]);
  const [segmentsLoading, setSegmentsLoading] = useState(false);
  const [exports, setExports] = useState<CsvExportModel[]>([]);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [exportSelectedForDeletion, setExportSelectedForDeletion] =
    useState<CsvExportModel>();

  useEffect(() => {
    setSegmentsLoading(true);
    api
      .genericExportsExportSegmentsList()
      .then(setSegments)
      .catch(alert)
      .finally(() => setSegmentsLoading(false));

    loadExports();
    console.log(csrfToken);
  }, []);

  function loadExports() {
    setExportsLoading(true);
    api
      .genericExportsCsvExportsList()
      .then(setExports)
      .catch(alert)
      .finally(() => setExportsLoading(false));
  }

  function deleteExport(exp: CsvExportModel) {
    api
      .genericExportsCsvExportsDestroy({ id: exp.id })
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
                <h5 className={"mb-0"}>CSV-Export Editor</h5>
                <TapirButton
                  variant={"outline-primary"}
                  text={"Neues Exports erzeugen"}
                  icon={"add_circle"}
                  onClick={() => setShowCreateModal(true)}
                  disabled={segmentsLoading}
                />
              </div>
            </Card.Header>
            <Card.Body>
              <CsvExportTable
                exports={exports}
                loading={exportsLoading}
                onExportEdit={() => {
                  alert("Not implemented");
                }}
                segments={segmentsLoading ? [] : segments}
                onExportDeleteClicked={setExportSelectedForDeletion}
              />
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <CsvExportCreateModal
        show={showCreateModal}
        onHide={() => setShowCreateModal(false)}
        segments={segments}
        loadExports={loadExports}
        csrfToken={csrfToken}
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
    </>
  );
};

export default CsvExportEditor;
