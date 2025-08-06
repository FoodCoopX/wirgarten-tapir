import React from "react";
import { Table } from "react-bootstrap";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { DEFAULT_PAGE_SIZE_BIG } from "../utils/pagination.ts";
import { WaitingListEntryDetails } from "../api-client";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import formatAddress from "../utils/formatAddress.ts";
import { formatDateText } from "../utils/formatDateText.ts";

interface WaitingListTableProps {
  loading: boolean;
  showCoopContent: boolean;
  waitingListEntries: WaitingListEntryDetails[];
  setSelectedEntryForEdition: (entry: WaitingListEntryDetails) => void;
}

const WaitingListTable: React.FC<WaitingListTableProps> = ({
  loading,
  showCoopContent,
  waitingListEntries,
  setSelectedEntryForEdition,
}) => {
  function buildWaitingListEntryRow(entry: WaitingListEntryDetails) {
    return (
      <tr
        key={entry.id}
        style={{ cursor: "pointer" }}
        onClick={() => setSelectedEntryForEdition(entry)}
        className={entry.linkSentDate ? "table-warning" : ""}
      >
        <td>
          <a
            onClick={(event) => event.stopPropagation()}
            href={entry.urlToMemberProfile}
          >
            {entry.memberNo}
          </a>
        </td>
        <td>{formatDateNumeric(entry.waitingSince)}</td>
        <td>{entry.linkSentDate && formatDateNumeric(entry.linkSentDate)}</td>
        <td>
          {entry.firstName} {entry.lastName}
        </td>
        <td>{entry.email}</td>
        <td>{entry.phoneNumber}</td>
        <td>
          {formatAddress(
            entry.street,
            entry.street2,
            entry.postcode,
            entry.city,
          )}
        </td>
        {showCoopContent && (
          <td>{formatDateNumeric(entry.dateOfEntryInCooperative)}</td>
        )}
        <td>
          {entry.currentProducts
            ?.map((product) => product.type.name + " " + product.name)
            .join(", ")}
        </td>
        <td>
          {entry.productWishes
            ?.map(
              (productWish) =>
                productWish.product.type.name + " " + productWish.product.name,
            )
            .join(", ")}
        </td>
        <td>{entry.currentPickupLocation?.name}</td>
        <td>
          {entry.pickupLocationWishes
            ?.map(
              (pickupLocationWish) => pickupLocationWish.pickupLocation.name,
            )
            .join(", ")}
        </td>
        {showCoopContent && <td>{entry.numberOfCoopShares}</td>}
        <td>
          {entry.desiredStartDate
            ? formatDateText(entry.desiredStartDate)
            : "so früh wie möglich"}
        </td>
        <td>{entry.category}</td>
        <td>{entry.comment}</td>
      </tr>
    );
  }

  return (
    <Table striped hover responsive className={"max-column-width"}>
      <thead>
        <tr>
          <th>Mitgliedsnummer</th>
          <th>Eintragungsdatum auf Warteliste</th>
          <th>Link Versand Datum</th>
          <th>Name</th>
          <th>Email-Adresse</th>
          <th>Telefonnummer</th>
          <th>Wohnort</th>
          {showCoopContent && <th>Geno-Beitrittsdatum</th>}
          <th>Aktuelle Produkte</th>
          <th>Gewünschte Produkte</th>
          <th>Derzeitiger Verteilort</th>
          <th>Verteilort Prioritäten</th>
          {showCoopContent && <th>Geno-Anteilen gewünscht</th>}
          <th>Wunsch-Startdatum</th>
          <th>Kategorie</th>
          <th>Kommentar</th>
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <PlaceholderTableRows
            nbRows={DEFAULT_PAGE_SIZE_BIG}
            nbColumns={showCoopContent ? 16 : 14}
            size={"xs"}
          />
        ) : (
          waitingListEntries.map(buildWaitingListEntryRow)
        )}
      </tbody>
    </Table>
  );
};

export default WaitingListTable;
