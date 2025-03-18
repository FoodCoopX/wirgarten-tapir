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

  function moveColumnUp(indexToMoveUp: number) {
    swapColumnIndexes(indexToMoveUp, indexToMoveUp - 1);
  }

  function moveColumnDown(indexToMoveDown: number) {
    swapColumnIndexes(indexToMoveDown, indexToMoveDown + 1);
  }

  function swapColumnIndexes(indexA: number, indexB: number) {
    const columnA = selectedColumns[indexA];
    const nameA = columnNames[indexA];
    const columnB = selectedColumns[indexB];
    const nameB = columnNames[indexB];
    selectedColumns[indexB] = columnA;
    columnNames[indexB] = nameA;
    selectedColumns[indexA] = columnB;
    columnNames[indexA] = nameB;

    onSelectedColumnsChange([...selectedColumns], [...columnNames]);
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
                  <span className={"d-flex flex-row gap-0"}>
                    <TapirButton
                      icon="arrow_drop_up"
                      variant={"outline-primary"}
                      size={"sm"}
                      disabled={index === 0}
                      onClick={() => moveColumnUp(index)}
                      type={"button"}
                    />
                    <TapirButton
                      icon="arrow_drop_down"
                      variant={"outline-primary"}
                      size={"sm"}
                      disabled={index === selectedColumns.length - 1}
                      onClick={() => moveColumnDown(index)}
                      type={"button"}
                    />
                    <TapirButton
                      icon={"delete"}
                      variant={"outline-danger"}
                      size={"sm"}
                      onClick={() => removeExportColumnFromSelection(column)}
                    />
                  </span>
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
