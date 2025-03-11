import React from "react";
import { Placeholder, Table } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import { CsvExportModel, ExportSegment } from "../api-client";

interface CsvExportTableProps {
  exports: CsvExportModel[];
  loading: boolean;
  onExportEdit: (exp: CsvExportModel) => void;
  segments: ExportSegment[];
  onExportDeleteClicked: (exp: CsvExportModel) => void;
}

const CsvExportEditor: React.FC<CsvExportTableProps> = ({
  exports,
  loading,
  onExportEdit,
  segments,
  onExportDeleteClicked,
}) => {
  function loadingPlaceholders() {
    return Array.from(Array(7).keys()).map((index) => {
      return (
        <tr key={index}>
          {Array.from(Array(3).keys()).map((index) => {
            return (
              <td key={index}>
                <Placeholder lg={10} />
              </td>
            );
          })}
        </tr>
      );
    });
  }

  function getSegmentName(segmentId: string) {
    for (const segment of segments) {
      if (segment.id === segmentId) return segment.displayName;
    }
    return "Unknown segment id: " + segmentId;
  }

  function loadedContent() {
    return exports.map((exp) => {
      return (
        <tr>
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
      <tbody>{loading ? loadingPlaceholders() : loadedContent()}</tbody>
    </Table>
  );
};

export default CsvExportEditor;
