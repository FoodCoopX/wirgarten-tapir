import React, { ChangeEvent } from "react";
import { Form, Table } from "react-bootstrap";
import { ExportSegmentColumn } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";

interface ColumnInputProps {
  onSelectedColumnsChange: (
    columns: ExportSegmentColumn[],
    columnNames: string[],
  ) => void;
  selectedColumns: ExportSegmentColumn[];
  columnNames: string[];
  autoFocus?: boolean;
  availableColumns: ExportSegmentColumn[];
}

const ColumnInput: React.FC<ColumnInputProps> = ({
  onSelectedColumnsChange,
  selectedColumns = [],
  columnNames,
  availableColumns,
}) => {
  function addExportColumnToSelection(columnId: string) {
    for (const column of availableColumns) {
      if (column.id === columnId) {
        onSelectedColumnsChange(
          [...selectedColumns, column],
          [...columnNames, ""],
        );
        return;
      }
    }
    alert("Column not found: " + columnId);
  }

  function removeExportColumnFromSelection(
    columnToRemove: ExportSegmentColumn,
  ) {
    const indexToRemove = selectedColumns.findIndex(
      (column) => column.id === columnToRemove.id,
    );
    const newSelectedColumns = [
      ...selectedColumns.slice(0, indexToRemove),
      ...selectedColumns.slice(indexToRemove + 1),
    ];
    const newColumnNames = [
      ...columnNames.slice(0, indexToRemove),
      ...columnNames.slice(indexToRemove + 1),
    ];
    onSelectedColumnsChange(newSelectedColumns, newColumnNames);
  }

  function onNameChanged(
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    index: number,
  ) {
    columnNames[index] = event.target.value;
    onSelectedColumnsChange(selectedColumns, [...columnNames]);
  }

  return (
    <>
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
      <Table striped hover responsive>
        <thead>
          <tr>
            <th>Interne Spaltenname</th>
            <th>Spaltenname in der exportierte Datei</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {selectedColumns.map((column, index) => {
            return (
              <tr key={column.id}>
                <td>
                  <span style={{ fontSize: ".875em" }} className={"text-wrap"}>
                    {column.displayName}
                  </span>
                </td>
                <td>
                  <Form.Control
                    type={"text"}
                    placeholder={column.displayName}
                    size={"sm"}
                    required={true}
                    value={columnNames[index]}
                    onChange={(event) => onNameChanged(event, index)}
                  ></Form.Control>
                </td>
                <td>
                  <TapirButton
                    icon={"delete"}
                    variant={"outline-danger"}
                    size={"sm"}
                    onClick={() => removeExportColumnFromSelection(column)}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </>
  );
};

export default ColumnInput;
