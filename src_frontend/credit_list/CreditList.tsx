import dayjs from "dayjs";
import LocaleData from "dayjs/plugin/localeData";
import React, { useEffect, useState } from "react";
import { Card, Col, Form, ListGroup, Row } from "react-bootstrap";
import { ExtendedMemberCredit, PaymentsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import CreateMemberCreditModal from "./CreateMemberCreditModal.tsx";
import CreditListTable from "./CreditListTable.tsx";

interface CreditListProps {
  csrfToken: string;
}

const CreditList: React.FC<CreditListProps> = ({ csrfToken }) => {
  const api = useApi(PaymentsApi, csrfToken);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [loading, setLoading] = useState(true);
  const [extendedMemberCredits, setExtendedMemberCredits] = useState<
    ExtendedMemberCredit[]
  >([]);
  const [monthFilter, setMonthFilter] = useState<number>(-1);
  const [yearFilter, setYearFilter] = useState<number | undefined>();
  const [showCreateModal, setShowCreateModal] = useState(false);

  dayjs.locale("de");
  dayjs.extend(LocaleData);

  useEffect(() => {
    loadCredits();
  }, [monthFilter, yearFilter]);

  function loadCredits() {
    setLoading(true);

    api
      .paymentsApiCreditListFilteredList({
        monthFilter: monthFilter,
        yearFilter: yearFilter,
      })
      .then(setExtendedMemberCredits)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Gutschriften",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  const totalAmount = extendedMemberCredits.reduce(
    (sum, credit) => sum + credit.credit.amount,
    0,
  );

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
                <h5 className={"mb-0"}>Gutschriften</h5>
                <TapirButton
                  variant={"outline-primary"}
                  text={"Gutschrift erzeugen"}
                  icon={"add_circle"}
                  onClick={() => setShowCreateModal(true)}
                />
              </div>
              <div className={"mt-2 text-muted"}>
                Offene Gutschriften gesamt: {formatCurrency(totalAmount)}
              </div>
            </Card.Header>
            <ListGroup>
              <ListGroup.Item>
                <Row>
                  <Col>
                    <Form.Group>
                      <Form.Label>Filter: Monat</Form.Label>
                      <Form.Select
                        value={monthFilter}
                        onChange={(event) =>
                          setMonthFilter(Number.parseInt(event.target.value))
                        }
                      >
                        <option key={-1} value={-1}>
                          Kein Filter
                        </option>
                        {dayjs.months().map((name, index) => {
                          return (
                            <option key={name} value={index + 1}>
                              {name}
                            </option>
                          );
                        })}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col>
                    <Form.Group>
                      <Form.Label>Filter: Jahr</Form.Label>
                      <Form.Control
                        type={"number"}
                        value={yearFilter}
                        onChange={(event) =>
                          event.target.value === ""
                            ? setYearFilter(undefined)
                            : setYearFilter(Number.parseInt(event.target.value))
                        }
                      ></Form.Control>
                    </Form.Group>
                  </Col>
                </Row>
              </ListGroup.Item>
              <ListGroup.Item>
                <CreditListTable
                  extendedMemberCredits={extendedMemberCredits}
                  loading={loading}
                />
              </ListGroup.Item>
            </ListGroup>
          </Card>
        </Col>
      </Row>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
      {showCreateModal && (
        <CreateMemberCreditModal
          csrfToken={csrfToken}
          setToastDatas={setToastDatas}
          onHide={() => setShowCreateModal(false)}
          show={showCreateModal}
          onCreditCreated={() => loadCredits()}
        />
      )}
    </>
  );
};

export default CreditList;
