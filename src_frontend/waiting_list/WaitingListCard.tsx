import React, { useEffect, useState } from "react";
import { Card, Col, Row, Table } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  PickupLocation,
  PickupLocationsApi,
  Product,
  SubscriptionsApi,
  WaitingListApi,
  WaitingListEntryDetails,
} from "../api-client";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BootstrapPagination from "../components/pagination/BootstrapPagination.tsx";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import formatAddress from "../utils/formatAddress.ts";
import { formatDateText } from "../utils/formatDateText.ts";
import "./waiting_list_card.css";
import WaitingListEntryEditModal from "./WaitingListEntryEditModal.tsx";

interface WaitingListCardProps {
  csrfToken: string;
}

const WaitingListCard: React.FC<WaitingListCardProps> = ({ csrfToken }) => {
  const waitingListApi = useApi(WaitingListApi, csrfToken);
  const pickupLocationApi = useApi(PickupLocationsApi, csrfToken);
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);
  const [waitingListEntries, setWaitingListEntries] = useState<
    WaitingListEntryDetails[]
  >([]);
  const [totalNumberOfEntries, setTotalNumberOfEntries] = useState(0);
  const [selectedEntryForEdition, setSelectedEntryForEdition] =
    useState<WaitingListEntryDetails>();
  const [pickupLocations, setPickupLocations] = useState<PickupLocation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [showCoopContent, setShowCoopContent] = useState(false);

  useEffect(() => {
    pickupLocationApi
      .pickupLocationsPickupLocationsList()
      .then(setPickupLocations)
      .catch(handleRequestError);

    subscriptionsApi
      .subscriptionsProductsList()
      .then(setProducts)
      .catch(handleRequestError);

    waitingListApi
      .waitingListApiCategoriesRetrieve()
      .then(setCategories)
      .catch(handleRequestError);

    waitingListApi
      .waitingListApiShowCoopContentRetrieve()
      .then(setShowCoopContent)
      .catch(handleRequestError);
  }, []);

  useEffect(() => {
    loadPage();
  }, [currentPage]);

  function loadPage() {
    setLoading(true);

    waitingListApi
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
  }

  function buildWaitingListEntryRow(entry: WaitingListEntryDetails) {
    return (
      <tr
        key={entry.id}
        style={{ cursor: "pointer" }}
        onClick={() => setSelectedEntryForEdition(entry)}
        className={entry.linkSentDate ? "table-warning" : ""}
      >
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
                      nbRows={DEFAULT_PAGE_SIZE}
                      nbColumns={showCoopContent ? 13 : 11}
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
      {selectedEntryForEdition && (
        <WaitingListEntryEditModal
          show={true}
          entryDetails={selectedEntryForEdition}
          csrfToken={csrfToken}
          onClose={() => setSelectedEntryForEdition(undefined)}
          reloadEntries={loadPage}
          pickupLocations={pickupLocations}
          products={products}
          categories={categories}
        />
      )}
    </>
  );
};

export default WaitingListCard;
