import React from "react";
import { CsvExport } from "../api-client";
import { Placeholder, Table } from "react-bootstrap";

interface CsvExportTableProps {
  exports: CsvExport[];
  loading: boolean;
}

const CsvExportEditor: React.FC<CsvExportTableProps> = ({
  exports,
  loading,
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

  function loadedContent() {
    return exports.map((exp) => {
      return (
        <tr>
          <td>{exp.name}</td>
          <td>{exp.description}</td>
          <td>{exp.exportSegmentName}</td>
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
        </tr>
      </thead>
      <tbody>{loading ? loadingPlaceholders() : loadedContent()}</tbody>
    </Table>
  );
};

export default CsvExportEditor;
