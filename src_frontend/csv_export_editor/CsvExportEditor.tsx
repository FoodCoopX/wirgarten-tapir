import React, { useEffect, useState } from "react";
import { Card, Col, Row } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import { CsvExport, ExportSegment, GenericExportsApi } from "../api-client";
import CsvExportTable from "./CsvExportTable.tsx";
import CsvExportCreateModal from "./CsvExportCreateModal.tsx";
import TapirButton from "../components/TapirButton.tsx";

const CsvExportEditor: React.FC = () => {
  const api = useApi(GenericExportsApi);
  const [segments, setSegments] = useState<ExportSegment[]>([]);
  const [segmentsLoading, setSegmentsLoading] = useState(false);
  const [exports, setExports] = useState<CsvExport[]>([]);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

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
      .genericExportsCsvExportListList()
      .then(setExports)
      .catch(alert)
      .finally(() => setExportsLoading(false));
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
              <CsvExportTable exports={exports} loading={exportsLoading} />
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <CsvExportCreateModal
        show={showCreateModal}
        onHide={() => setShowCreateModal(false)}
        segments={segments}
        loadExports={loadExports}
      />
    </>
  );
};

export default CsvExportEditor;
