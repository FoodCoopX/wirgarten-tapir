import React from "react";
import { Card, Table } from "react-bootstrap";

import type { ContractCreationError } from "../types.ts";

interface ContractErrorsCardProps {
  errors: ContractCreationError[];
}

const ContractErrorsCard: React.FC<ContractErrorsCardProps> = ({ errors }) => {
  if (errors.length === 0) {
    return null;
  }
  return (
    <Card className="mb-4 border-danger">
      <Card.Header className="bg-danger text-white">
        {"Fehler bei der Vertragserzeugung"}
      </Card.Header>
      <Card.Body>
        <Table size="sm" className="mb-0">
          <thead>
            <tr>
              <th>{"Mitglied"}</th>
              <th>{"Produkt"}</th>
              <th>{"Grund"}</th>
            </tr>
          </thead>
          <tbody>
            {errors.map((error) => (
              <tr
                key={`${error.memberId}:${error.productName ?? ""}:${error.error ?? ""}`}
              >
                <td>{error.memberName ?? error.memberId}</td>
                <td>{error.productName ?? "–"}</td>
                <td>{error.error ?? "–"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card.Body>
    </Card>
  );
};

export default ContractErrorsCard;
