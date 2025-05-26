import React, { ChangeEvent } from "react";
import { Form, Table } from "react-bootstrap";
import { ExportSegmentColumn } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";

interface ColumnInputProps {
  onSelectedColumnsChange: (
    columnsIds: string[],
    columnNames: string[],
  ) => void;
  selectedColumnIds: string[];
  columnNames: string[];
  autoFocus?: boolean;
  availableColumns: ExportSegmentColumn[];
}

const ColumnInput: React.FC<ColumnInputProps> = ({
  onSelectedColumnsChange,
  selectedColumnIds,
  columnNames,
  availableColumns,
}) => {
  function addExportColumnToSelection(columnId: string) {
    if (columnId === "") {
      onSelectedColumnsChange([...selectedColumnIds, ""], [...columnNames, ""]);
      return;
    }

    for (const column of availableColumns) {
      if (column.id === columnId) {
        onSelectedColumnsChange(
          [...selectedColumnIds, column.id],
          [...columnNames, column.displayName],
        );
        return;
      }
    }

    alert("Column not found: " + columnId);
  }

  function removeExportColumnFromSelection(columnIdToRemove: string) {
    const indexToRemove = selectedColumnIds.findIndex(
      (columnId) => columnId === columnIdToRemove,
    );
    const newSelectedColumns = [
      ...selectedColumnIds.slice(0, indexToRemove),
      ...selectedColumnIds.slice(indexToRemove + 1),
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
    onSelectedColumnsChange(selectedColumnIds, [...columnNames]);
  }

  function moveColumnUp(indexToMoveUp: number) {
    swapColumnIndexes(indexToMoveUp, indexToMoveUp - 1);
  }

  function moveColumnDown(indexToMoveDown: number) {
    swapColumnIndexes(indexToMoveDown, indexToMoveDown + 1);
  }

  function swapColumnIndexes(indexA: number, indexB: number) {
    const columnA = selectedColumnIds[indexA];
    const nameA = columnNames[indexA];
    const columnB = selectedColumnIds[indexB];
    const nameB = columnNames[indexB];
    selectedColumnIds[indexB] = columnA;
    columnNames[indexB] = nameA;
    selectedColumnIds[indexA] = columnB;
    columnNames[indexA] = nameB;

    onSelectedColumnsChange([...selectedColumnIds], [...columnNames]);
  }

  function getColumnDisplayName(columnId: string) {
    if (columnId === "") {
      return "Leere Spalte";
    }

    for (const column of availableColumns) {
      if (column.id === columnId) {
        return column.displayName;
      }
    }

    return "Unknown column: " + columnId;
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
          .filter((column) => !selectedColumnIds.includes(column.id))
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
          {selectedColumnIds.map((columnId, index) => {
            return (
              <tr key={columnId}>
                <td>
                  <span style={{ fontSize: ".875em" }} className={"text-wrap"}>
                    {getColumnDisplayName(columnId)}
                  </span>
                </td>
                <td>
                  <Form.Control
                    type={"text"}
                    placeholder={getColumnDisplayName(columnId)}
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
                      disabled={index === selectedColumnIds.length - 1}
                      onClick={() => moveColumnDown(index)}
                      type={"button"}
                    />
                    <TapirButton
                      icon={"delete"}
                      variant={"outline-danger"}
                      size={"sm"}
                      onClick={() => removeExportColumnFromSelection(columnId)}
                    />
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3}>
              <TapirButton
                icon={"add_column_right"}
                text={"Leere Spalte hinzufügen"}
                variant={"outline-primary"}
                size={"sm"}
                onClick={() => addExportColumnToSelection("")}
              />
            </td>
          </tr>
        </tfoot>
      </Table>
    </>
  );
};

export default ColumnInput;
