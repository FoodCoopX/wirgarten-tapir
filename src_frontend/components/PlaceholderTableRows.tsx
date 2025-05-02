import React from "react";
import { Placeholder } from "react-bootstrap";
import { PlaceholderSize } from "react-bootstrap/usePlaceholder";

interface PlaceholderTableRowsProps {
  nbRows: number;
  nbColumns: number;
  size: PlaceholderSize;
}

const PlaceholderTableRows: React.FC<PlaceholderTableRowsProps> = ({
  nbRows,
  nbColumns,
  size,
}) => {
  return [...Array(nbRows)].map((_, indexTr) => (
    <tr key={indexTr}>
      {[...Array(nbColumns)].map((_, indexTd) => (
        <td key={indexTd}>
          <Placeholder animation={"wave"} size={size}>
            <Placeholder xs={2} size={size} />
          </Placeholder>
        </td>
      ))}
    </tr>
  ));
};

export default PlaceholderTableRows;
