import React from "react";
import { Badge, Form } from "react-bootstrap";
import { ExportSegmentColumn } from "../api-client";

interface ColumnInputProps {
  onSelectedColumnsChange: (columns: ExportSegmentColumn[]) => void;
  selectedColumns: ExportSegmentColumn[];
  autoFocus?: boolean;
  availableColumns: ExportSegmentColumn[];
}

const ColumnInput: React.FC<ColumnInputProps> = ({
  onSelectedColumnsChange,
  selectedColumns = [],
  availableColumns,
}) => {
  function addExportColumnToSelection(columnId: string) {
    for (const column of availableColumns) {
      if (column.id === columnId) {
        onSelectedColumnsChange([...selectedColumns, column]);
        return;
      }
    }
    alert("Column not found: " + columnId);
  }

  function removeExportColumnFromSelection(
    columnToRemove: ExportSegmentColumn,
  ) {
    onSelectedColumnsChange(
      selectedColumns.filter((column) => column.id !== columnToRemove.id),
    );
  }

  return (
    <>
      <div className={"d-flex flex-column gap-2 mb-1"}>
        {Array.from(selectedColumns).map((column) => (
          <div>
            <Badge
              onClick={() => removeExportColumnFromSelection(column)}
              style={{ cursor: "pointer" }}
              key={column.id}
            >
              {column.displayName}
            </Badge>{" "}
            <Form.Text>{column.description}</Form.Text>
          </div>
        ))}
      </div>
      <Form.Select
        onChange={(event) => {
          addExportColumnToSelection(event.target.value);
        }}
      >
        <option value=""></option>
        {availableColumns
          .filter((column) => !selectedColumns.includes(column))
          .map((column) => (
            <option value={column.id} key={column.id}>
              {column.displayName}
            </option>
          ))}
      </Form.Select>
      <Form.Text>Click on a selected column to deselect it.</Form.Text>
    </>
  );
};

export default ColumnInput;
