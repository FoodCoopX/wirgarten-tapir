import React from "react";
import { Table } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import { ExportSegment, PdfExportModel } from "../api-client";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";

interface PdfExportTableProps {
  exports: PdfExportModel[];
  loading: boolean;
  onExportEdit: (exp: PdfExportModel) => void;
  segments: ExportSegment[];
  onExportDeleteClicked: (exp: PdfExportModel) => void;
  onExportBuildClicked: (exp: PdfExportModel) => void;
}

const PdfExportTable: React.FC<PdfExportTableProps> = ({
  exports,
  loading,
  onExportEdit,
  segments,
  onExportDeleteClicked,
  onExportBuildClicked,
}) => {
  function getSegmentName(segmentId: string) {
    for (const segment of segments) {
      if (segment.id === segmentId) return segment.displayName;
    }
    return "Unknown segment id: " + segmentId;
  }

  function loadedContent() {
    return exports.map((exp) => {
      return (
        <tr key={exp.id}>
          <td>{exp.name}</td>
          <td>{exp.description}</td>
          <td>{getSegmentName(exp.exportSegmentId)}</td>
          <td>
            <div className={"d-flex flex-row gap-2"}>
              <TapirButton
                variant={"outline-primary"}
                icon={"edit"}
                size={"sm"}
                onClick={() => onExportEdit(exp)}
              />
              <TapirButton
                variant={"outline-primary"}
                icon={"attach_file"}
                size={"sm"}
                onClick={() => onExportBuildClicked(exp)}
              />
              <TapirButton
                variant={"outline-danger"}
                icon={"delete"}
                size={"sm"}
                onClick={() => onExportDeleteClicked(exp)}
              />
            </div>
          </td>
        </tr>
      );
    });
  }

  return (
    <Table striped hover responsive>
      <thead>
        <tr>
          <th>Name</th>
          <th>Beschreibung</th>
          <th>Datensatz</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <PlaceholderTableRows nbRows={7} nbColumns={3} size={"lg"} />
        ) : (
          loadedContent()
        )}
      </tbody>
    </Table>
  );
};

export default PdfExportTable;
