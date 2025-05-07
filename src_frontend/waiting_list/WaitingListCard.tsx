import React, { useEffect, useState } from "react";
import { Card, Col, Row, Table } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import { WaitingListApi, WaitingListEntry } from "../api-client";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BootstrapPagination from "../components/pagination/BootstrapPagination.tsx";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import formatAddress from "../utils/formatAddress.ts";
import { formatDateText } from "../utils/formatDateText.ts";
import "./waiting_list_card.css";

interface WaitingListCardProps {
  csrfToken: string;
}

const WaitingListCard: React.FC<WaitingListCardProps> = ({ csrfToken }) => {
  const api = useApi(WaitingListApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);
  const [waitingListEntries, setWaitingListEntries] = useState<
    WaitingListEntry[]
  >([]);
  const [totalNumberOfEntries, setTotalNumberOfEntries] = useState(0);

  useEffect(() => {
    api
      .waitingListApiListList({
        limit: DEFAULT_PAGE_SIZE,
        offset: DEFAULT_PAGE_SIZE * currentPage,
      })
      .then((paginatedData) => {
        setWaitingListEntries(paginatedData.results);
        setTotalNumberOfEntries(paginatedData.count);
      })
      .catch(handleRequestError)
      .finally(() => setLoading(false));
  }, [currentPage]);

  function buildWaitingListEntryRow(entry: WaitingListEntry) {
    return (
      <tr key={entry.id}>
        <td>{entry.memberNo}</td>
        <td>{formatDateNumeric(entry.waitingSince)}</td>
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
        <td>{formatDateNumeric(entry.dateOfEntryInCooperative)}</td>
        <td>
          {entry.currentProducts
            ?.map((product) => product.type.name + " " + product.name)
            .join(", ")}
        </td>
        <td>
          {entry.productWishes
            ?.map((product) => product.type.name + " " + product.name)
            .join(", ")}
        </td>
        <td>{entry.currentPickupLocation?.name}</td>
        <td>
          {entry.pickupLocationWishes
            ?.map((pickupLocation) => pickupLocation.name)
            .join(", ")}
        </td>
        <td>{entry.numberOfCoopShares}</td>
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
    <>
      <Row className={"mt-4"}>
        <Col>
          <Card>
            <Card.Header>
              <div
                className={
                  "d-flex justify-content-between align-items-center mb-0"
                }
              >
                <h5 className={"mb-0"}>Warteliste</h5>
              </div>
            </Card.Header>
            <Card.Body className={"p-0"}>
              <Table striped hover responsive className={"max-column-width"}>
                <thead>
                  <tr>
                    <th>Mitgliedsnummer</th>
                    <th>Eintragungsdatum auf Warteliste</th>
                    <th>Name</th>
                    <th>Email-Adresse</th>
                    <th>Telefonnummer</th>
                    <th>Wohnort</th>
                    <th>Geno-Beitrittsdatum</th>
                    <th>Aktuelle Produkte</th>
                    <th>Gewünschte Produkte</th>
                    <th>Derzeitiger Verteilort</th>
                    <th>Verteilort Prioritäten</th>
                    <th>Geno-Anteilen gewünscht</th>
                    <th>Wunsch-Startdatum</th>
                    <th>Kategorie</th>
                    <th>Kommentar</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <PlaceholderTableRows
                      nbRows={DEFAULT_PAGE_SIZE}
                      nbColumns={13}
                      size={"xs"}
                    />
                  ) : (
                    waitingListEntries.map(buildWaitingListEntryRow)
                  )}
                </tbody>
              </Table>
            </Card.Body>
            <Card.Footer>
              <BootstrapPagination
                currentPage={currentPage}
                pageSize={DEFAULT_PAGE_SIZE}
                itemCount={totalNumberOfEntries}
                goToPage={setCurrentPage}
              />
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default WaitingListCard;
