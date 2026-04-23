import React from "react";
import { Form, Table } from "react-bootstrap";
import { ExtendedMemberCredit } from "../api-client";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

interface CreditListTableProps {
  extendedMemberCredits: ExtendedMemberCredit[];
  loading: boolean;
  selectedIds: Set<string>;
  onSelectionChange: (id: string, checked: boolean) => void;
}

const CreditListTable: React.FC<CreditListTableProps> = ({
  extendedMemberCredits,
  loading,
  selectedIds,
  onSelectionChange,
}) => {
  return (
    <Table striped hover responsive>
      <thead style={{ textAlign: "center" }}>
        <tr>
          <th>#</th>
          <th>Mandatsreferenz</th>
          <th>Mitgliedsnummer</th>
          <th>Mitgliedsname</th>
          <th>IBAN</th>
          <th>Verwendungszweck</th>
          <th>Wert</th>
          <th>Kommentar</th>
          <th>Datum</th>
          <th>Gebucht am</th>
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <PlaceholderTableRows
            nbColumns={9}
            nbRows={
              extendedMemberCredits.length > 0
                ? extendedMemberCredits.length
                : 20
            }
            size={"lg"}
          />
        ) : (
          extendedMemberCredits.map((extendedMemberCredit) => {
            const creditId: string = extendedMemberCredit.credit.id ?? "";
            const isSelected = selectedIds.has(creditId);
            return (
              <tr
                key={creditId}
                className={extendedMemberCredit.credit.accountedOn ? "table-success" : ""}
              >
                <td>
                  <Form.Check
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      onSelectionChange(creditId, e.target.checked)
                    }
                    disabled={!!extendedMemberCredit.credit.accountedOn}
                  />
                </td>
                <td>{extendedMemberCredit.mandateRef}</td>
                <td>{extendedMemberCredit.member.memberNo}</td>
                <td>
                  <a href={extendedMemberCredit.memberUrl}>
                    {extendedMemberCredit.member.firstName}{" "}
                    {extendedMemberCredit.member.lastName}
                  </a>
                </td>
                <td>{extendedMemberCredit.member.iban}</td>
                <td>{extendedMemberCredit.credit.purpose}</td>
                <td>{formatCurrency(extendedMemberCredit.credit.amount)}</td>
                <td>{extendedMemberCredit.credit.comment}</td>
                <td>
                  {formatDateNumeric(extendedMemberCredit.credit.dueDate)}
                </td>
                <td>
                  {extendedMemberCredit.credit.accountedOn
                    ? formatDateNumeric(extendedMemberCredit.credit.accountedOn)
                    : "-"}
                </td>
              </tr>
            );
          })
        )}
      </tbody>
    </Table>
  );
};

export default CreditListTable;
