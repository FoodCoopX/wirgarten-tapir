import React, { useEffect, useState } from "react";
import {
  Badge,
  Card,
  Col,
  Form,
  ListGroup,
  Row,
  Tab,
  Tabs,
} from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  Counts,
  PickupLocation,
  PickupLocationsApi,
  Product,
  SubscriptionsApi,
  WaitingListApi,
  WaitingListApiListListEntryTypeEnum,
  WaitingListApiListListMemberTypeEnum,
  WaitingListApiListListOrderByEnum,
  WaitingListEntryDetails,
} from "../api-client";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BootstrapPagination from "../components/pagination/BootstrapPagination.tsx";
import "./waiting_list_card.css";
import WaitingListEntryEditModal from "./WaitingListEntryEditModal.tsx";
import { ToastData } from "../types/ToastData.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import WaitingListTable from "./WaitingListTable.tsx";

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
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [filterMemberType, setFilterMemberType] =
    useState<WaitingListApiListListMemberTypeEnum>("all");
  const [filterEntryType, setFilterEntryType] =
    useState<WaitingListApiListListEntryTypeEnum>("any");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterCurrentPickupLocation, setFilterCurrentPickupLocation] =
    useState("");
  const [filterPickupLocationWish, setFilterPickupLocationWish] = useState("");
  const [filterProductWish, setFilterProductWish] = useState("");
  const [orderBy, setOrderBy] =
    useState<WaitingListApiListListOrderByEnum>("-created_at");
  const [counts, setCounts] = useState<Counts>();

  useEffect(() => {
    pickupLocationApi
      .pickupLocationsPickupLocationsList()
      .then(setPickupLocations)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verteilstationen",
          setToastDatas,
        ),
      );

    subscriptionsApi
      .subscriptionsProductsList()
      .then(setProducts)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Produkte",
          setToastDatas,
        ),
      );

    waitingListApi
      .waitingListApiCategoriesRetrieve()
      .then(setCategories)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Kategorien",
          setToastDatas,
        ),
      );

    waitingListApi
      .waitingListApiShowCoopContentRetrieve()
      .then(setShowCoopContent)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Geno-Daten",
          setToastDatas,
        ),
      );

    waitingListApi
      .waitingListApiCountsRetrieve()
      .then(setCounts)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Anzahl an Einträge",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    loadPage();
  }, [
    currentPage,
    filterMemberType,
    filterEntryType,
    filterCategory,
    filterCurrentPickupLocation,
    filterPickupLocationWish,
    filterProductWish,
    orderBy,
  ]);

  function loadPage() {
    setLoading(true);

    waitingListApi
      .waitingListApiListList({
        limit: DEFAULT_PAGE_SIZE,
        offset: DEFAULT_PAGE_SIZE * currentPage,
        memberType: filterMemberType,
        entryType: filterEntryType,
        category: filterCategory,
        currentPickupLocationId: filterCurrentPickupLocation,
        pickupLocationWish: filterPickupLocationWish,
        productWish: filterProductWish,
        orderBy: orderBy,
      })
      .then((paginatedData) => {
        setWaitingListEntries(paginatedData.results);
        setTotalNumberOfEntries(paginatedData.count);

        if (selectedEntryForEdition) {
          const reloadedEntry = paginatedData.results.find(
            (entry) => entry.id === selectedEntryForEdition.id,
          );
          if (reloadedEntry) {
            setSelectedEntryForEdition(reloadedEntry);
          }
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Warteliste-Einträge",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
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
              <Tabs
                defaultActiveKey={"all"}
                onSelect={(memberType) =>
                  setFilterMemberType(
                    memberType as WaitingListApiListListMemberTypeEnum,
                  )
                }
              >
                <Tab
                  eventKey={"all"}
                  title={
                    <span>
                      Alle <Badge>{counts?.all}</Badge>
                    </span>
                  }
                />
                <Tab
                  eventKey={"new_members"}
                  title={
                    <span>
                      Interessent*innen <Badge>{counts?.newMembers}</Badge>
                    </span>
                  }
                />
                <Tab
                  eventKey={"existing_members"}
                  title={
                    <span>
                      Bestehende Mitglieder{" "}
                      <Badge>{counts?.existingMembers}</Badge>
                    </span>
                  }
                />
              </Tabs>
            </Card.Header>
            <ListGroup>
              <ListGroup.Item>
                <Row>
                  <Col>
                    <Form.Group>
                      <Form.Label>Art der Wünsche: </Form.Label>
                      <Form.Select
                        onChange={(event) =>
                          setFilterEntryType(
                            event.target
                              .value as WaitingListApiListListEntryTypeEnum,
                          )
                        }
                      >
                        <option value="any">Alle</option>
                        <option value="must_have_pickup_location_wish">
                          Muss ein Verteilort-Wunsch beinhalten
                        </option>
                        <option value="must_have_product_wish">
                          Muss ein Produkt-Wunsch beinhalten
                        </option>
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col>
                    <Form.Group>
                      <Form.Label>Kategorie: </Form.Label>
                      <Form.Select
                        onChange={(event) =>
                          setFilterCategory(event.target.value)
                        }
                      >
                        <option value="any">Alle</option>
                        <option value="none">Keine</option>
                        {categories.map((category) => (
                          <option key={category} value={category}>
                            {category}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  {filterMemberType !== "new_members" && (
                    <Col>
                      <Form.Group>
                        <Form.Label>Derzeitiger Verteilort:</Form.Label>
                        <Form.Select
                          onChange={(event) =>
                            setFilterCurrentPickupLocation(event.target.value)
                          }
                        >
                          <option value="">Filter ausgeschaltet</option>
                          {pickupLocations.map((pickupLocation) => (
                            <option
                              key={pickupLocation.id}
                              value={pickupLocation.id}
                            >
                              {pickupLocation.name}
                            </option>
                          ))}
                        </Form.Select>
                      </Form.Group>
                    </Col>
                  )}
                </Row>
                <Row className={"mt-2"}>
                  <Col>
                    <Form.Group>
                      <Form.Label>Verteilort-Wunsch:</Form.Label>
                      <Form.Select
                        onChange={(event) =>
                          setFilterPickupLocationWish(event.target.value)
                        }
                      >
                        <option value="">Filter ausgeschaltet</option>
                        {pickupLocations.map((pickupLocation) => (
                          <option
                            key={pickupLocation.id}
                            value={pickupLocation.id}
                          >
                            {pickupLocation.name}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col>
                    <Form.Group>
                      <Form.Label>Produkt-Wunsch:</Form.Label>
                      <Form.Select
                        onChange={(event) =>
                          setFilterProductWish(event.target.value)
                        }
                      >
                        <option value="">Filter ausgeschaltet</option>
                        {products.map((product) => (
                          <option key={product.id} value={product.id}>
                            {product.type.name}: {product.name}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col>
                    <Form.Group>
                      <Form.Label>Sortieren nach:</Form.Label>
                      <Form.Select
                        onChange={(event) =>
                          setOrderBy(
                            event.target
                              .value as WaitingListApiListListOrderByEnum,
                          )
                        }
                      >
                        <option value="-created_at">
                          Eintragungsdatum auf der Warteliste (absteigend)
                        </option>
                        <option value="created_at">
                          Eintragungsdatum auf der Warteliste (aufsteigend)
                        </option>
                        {filterMemberType !== "new_members" && (
                          <>
                            <option value="-member_since">
                              Eintrittsdatum zur Geno (absteigend)
                            </option>
                            <option value="member_since">
                              Eintrittsdatum zur Geno (aufsteigend)
                            </option>
                          </>
                        )}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                </Row>
              </ListGroup.Item>
              <ListGroup.Item>
                <WaitingListTable
                  waitingListEntries={waitingListEntries}
                  setSelectedEntryForEdition={setSelectedEntryForEdition}
                  loading={loading}
                  showCoopContent={showCoopContent}
                />
              </ListGroup.Item>
            </ListGroup>
            <Card.Footer>
              <div
                className={"d-flex justify-content-center"}
                style={{ width: "100%" }}
              >
                <BootstrapPagination
                  currentPage={currentPage}
                  pageSize={DEFAULT_PAGE_SIZE}
                  itemCount={totalNumberOfEntries}
                  goToPage={setCurrentPage}
                />
              </div>
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
          setToastDatas={setToastDatas}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default WaitingListCard;
