import React from "react";
import { Table } from "react-bootstrap";
import { ExtendedMemberCredit } from "../api-client";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

interface CreditListTableProps {
  extendedMemberCredits: ExtendedMemberCredit[];
  loading: boolean;
}

const CreditListTable: React.FC<CreditListTableProps> = ({
  extendedMemberCredits,
  loading,
}) => {
  return (
    <Table striped hover responsive>
      <thead style={{ textAlign: "center" }}>
        <tr>
          <th>Mandatsreferenz</th>
          <th>Mitgliedsnummer</th>
          <th>Mitgliedsname</th>
          <th>IBAN</th>
          <th>Verwendungszweck</th>
          <th>Wert</th>
          <th>Kommentar</th>
          <th>Datum</th>
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <PlaceholderTableRows
            nbColumns={8}
            nbRows={
              extendedMemberCredits.length > 0
                ? extendedMemberCredits.length
                : 20
            }
            size={"lg"}
          />
        ) : (
          extendedMemberCredits.map((extendedMemberCredit) => (
            <tr key={extendedMemberCredit.credit.id}>
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
              <td>{formatDateNumeric(extendedMemberCredit.credit.dueDate)}</td>
            </tr>
          ))
        )}
      </tbody>
    </Table>
  );
};

export default CreditListTable;
