import React, { useEffect, useState } from "react";
import { Col, Form, ListGroup, Modal, Row, Spinner } from "react-bootstrap";
import { DeliveriesApi, DeliveryDayAdjustment } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import dayjs from "dayjs";
import TapirButton from "../components/TapirButton.tsx";
import { getPeriodIdFromUrl } from "./get_parameter_from_url.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface GrowingPeriodModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
}

const GrowingPeriodModal: React.FC<GrowingPeriodModalProps> = ({
  show,
  onHide,
  csrfToken,
}) => {
  const api = useApi(DeliveriesApi, csrfToken);
  const [startDate, setStartDate] = useState<Date>(new Date());
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [weeksWithoutDelivery, setWeeksWithoutDelivery] = useState<number[]>(
    [],
  );
  const [adjustments, setAdjustments] = useState<DeliveryDayAdjustment[]>([]);
  const [jokersEnabled, setJokersEnabled] = useState(false);
  const [maxJokersPerMember, setMaxJokersPerMember] = useState(0);
  const [jokerRestrictions, setJokerRestrictions] = useState("");
  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!show) return;

    setDataLoading(true);

    if (!getPeriodIdFromUrl()) return;

    api
      .deliveriesApiGrowingPeriodWithAdjustmentsRetrieve({
        growingPeriodId: getPeriodIdFromUrl(),
      })
      .then((response) => {
        setStartDate(response.growingPeriodStartDate);
        setEndDate(response.growingPeriodEndDate);
        setWeeksWithoutDelivery(response.growingPeriodWeeksWithoutDelivery);
        setAdjustments(response.adjustments);
        setJokersEnabled(response.jokersEnabled);
        setMaxJokersPerMember(response.maxJokersPerMember);
        setJokerRestrictions(response.jokerRestrictions);
      })
      .catch(handleRequestError)
      .finally(() => setDataLoading(false));
  }, [show]);

  function onSave() {
    const form = document.getElementById(
      "growingPeriodForm",
    ) as HTMLFormElement;
    if (!form.reportValidity()) return;

    setSaving(true);

    api
      .deliveriesApiGrowingPeriodWithAdjustmentsPartialUpdate({
        patchedGrowingPeriodWithDeliveryDayAdjustmentsRequest: {
          growingPeriodId: getPeriodIdFromUrl(),
          growingPeriodStartDate: startDate,
          growingPeriodEndDate: endDate,
          growingPeriodWeeksWithoutDelivery: weeksWithoutDelivery,
          adjustments: adjustments,
          jokerRestrictions: jokerRestrictions,
          maxJokersPerMember: maxJokersPerMember,
        },
      })
      .then(() => location.reload())
      .catch(handleRequestError)
      .finally(() => setSaving(false));
  }

  function onWeekWithoutDeliveryChanged(index: number, newWeek: number) {
    const newWeeks = [...weeksWithoutDelivery];
    newWeeks[index] = newWeek;
    setWeeksWithoutDelivery(newWeeks);
  }

  function onWeekWithoutDeliveryAdd() {
    setWeeksWithoutDelivery([...weeksWithoutDelivery, 1]);
  }

  function onWeekWithoutDeliveryDelete(index: number) {
    const newWeeks = [
      ...weeksWithoutDelivery.slice(0, index),
      ...weeksWithoutDelivery.slice(index + 1),
    ];
    setWeeksWithoutDelivery(newWeeks);
  }

  function onAdjustmentWeekAdd() {
    const newAdjustments = [...adjustments];
    newAdjustments.push({
      calendarWeek: 1,
      adjustedWeekday: 0,
    });
    setAdjustments(newAdjustments);
  }

  function onAdjustmentWeekChanged(index: number, newWeek: number) {
    const newAdjustments = [...adjustments];
    newAdjustments[index].calendarWeek = newWeek;
    setAdjustments(newAdjustments);
  }

  function onAdjustmentWeekdayChanged(index: number, newWeekday: number) {
    const newAdjustments = [...adjustments];
    newAdjustments[index].adjustedWeekday = newWeekday;
    setAdjustments(newAdjustments);
  }

  function onAdjustmentDelete(index: number) {
    const newAdjustments = [
      ...adjustments.slice(0, index),
      ...adjustments.slice(index + 1),
    ];
    setAdjustments(newAdjustments);
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    return (
      <ListGroup variant={"flush"}>
        <Form id={"growingPeriodForm"}>
          <ListGroup.Item>
            <Row>
              <Col>
                <Form.Group className={"mb-2"}>
                  <Form.Label>Anfangsdatum</Form.Label>
                  <Form.Control
                    type={"date"}
                    onChange={(event) =>
                      setStartDate(new Date(event.target.value))
                    }
                    required={true}
                    value={dayjs(startDate).format("YYYY-MM-DD")}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group className={"mb-2"}>
                  <Form.Label>Enddatum</Form.Label>
                  <Form.Control
                    type={"date"}
                    onChange={(event) =>
                      setEndDate(new Date(event.target.value))
                    }
                    required={true}
                    value={dayjs(endDate).format("YYYY-MM-DD")}
                  />
                </Form.Group>
              </Col>
            </Row>
          </ListGroup.Item>
          {jokersEnabled && (
            <ListGroup.Item>
              <Row>
                <Col>
                  <Form.Group className={"mb-2"}>
                    <Form.Label>
                      Maximal Anzahl an Joker per Mitglied
                    </Form.Label>
                    <Form.Control
                      type={"number"}
                      onChange={(event) =>
                        setMaxJokersPerMember(parseInt(event.target.value))
                      }
                      required={true}
                      value={maxJokersPerMember}
                    />
                  </Form.Group>
                </Col>
              </Row>
              <Row>
                <Col>
                  <Form.Group className={"mb-2"}>
                    <Form.Label>Joker Einschränkungen</Form.Label>
                    <Form.Control
                      type={"text"}
                      onChange={(event) =>
                        setJokerRestrictions(event.target.value)
                      }
                      required={true}
                      value={jokerRestrictions}
                    />
                    <Form.Text>
                      Zeiträume, in denen das Mitglied nur eine begrenzte Anzahl
                      an Jokern setzen kann. zB: maximal 2 Joker pro Mitglied im
                      August. <br />
                      Format:
                      StartDatum-EndDatum[AnzahlJoker];StartDatum-EndDatum[AnzahlJoker]{" "}
                      <br />
                      Beispiel: 01.08.-31.08.[2];15.02.-20.03.[3] heißt maximal
                      2 Joker im Zeitraum 01.08. - 31.08. und maximal 3 Joker im
                      Zeitraum 15.02. - 20.03.. <br />
                      Wenn es keine Einschränkungen geben soll, bitte "disabled"
                      eintragen.
                    </Form.Text>
                  </Form.Group>
                </Col>
              </Row>
            </ListGroup.Item>
          )}
          <ListGroup.Item>
            <Row>
              <Col>
                <Form.Group>
                  <Form.Label>Lieferfreie Wochen (als KW)</Form.Label>
                  <div className={"d-flex flex-column gap-2 mb-2"}>
                    {weeksWithoutDelivery?.map((weekNumber, index) => {
                      return (
                        <div key={index} className={"d-flex flex-row gap-2"}>
                          <Form.Control
                            type={"number"}
                            min={1}
                            max={53}
                            step={1}
                            value={weekNumber}
                            onChange={(event) => {
                              onWeekWithoutDeliveryChanged(
                                index,
                                parseInt(event.target.value),
                              );
                            }}
                          />
                          <TapirButton
                            variant={"outline-danger"}
                            icon={"delete"}
                            size={"sm"}
                            onClick={() => onWeekWithoutDeliveryDelete(index)}
                          />
                        </div>
                      );
                    })}
                  </div>
                </Form.Group>
                <TapirButton
                  type={"button"}
                  text={"Lieferfreie Woche hinzufügen"}
                  size={"sm"}
                  icon={"calendar_add_on"}
                  variant={"outline-primary"}
                  onClick={onWeekWithoutDeliveryAdd}
                />
              </Col>
              <Col>
                <Form.Group>
                  <Form.Label>Abweichende Ausliefertage</Form.Label>
                  <div className={"d-flex flex-column gap-2 mb-2"}>
                    {adjustments?.map((adjustment, index) => {
                      return (
                        <div
                          key={index}
                          className={
                            "d-flex flex-row gap-2 align-items-stretch"
                          }
                        >
                          <div
                            className={
                              "d-flex flex-column justify-content-center"
                            }
                          >
                            <Form.Label
                              className={"mb-0"}
                              id={"label-kw-adjustment-" + index}
                            >
                              KW
                            </Form.Label>
                          </div>
                          <Form.Control
                            type={"number"}
                            min={1}
                            max={53}
                            step={1}
                            value={adjustment.calendarWeek}
                            onChange={(event) => {
                              onAdjustmentWeekChanged(
                                index,
                                parseInt(event.target.value),
                              );
                            }}
                            aria-labelledby={"label-kw-adjustment-" + index}
                          />
                          <Form.Select
                            onChange={(event) => {
                              onAdjustmentWeekdayChanged(
                                index,
                                parseInt(event.target.value),
                              );
                            }}
                            value={adjustment.adjustedWeekday}
                          >
                            <option value={0}>Montag</option>
                            <option value={1}>Dienstag</option>
                            <option value={2}>Mittwoch</option>
                            <option value={3}>Donnerstag</option>
                            <option value={4}>Freitag</option>
                            <option value={5}>Samstag</option>
                            <option value={6}>Sonntag</option>
                          </Form.Select>
                          <TapirButton
                            variant={"outline-danger"}
                            icon={"delete"}
                            size={"sm"}
                            onClick={() => onAdjustmentDelete(index)}
                          />
                        </div>
                      );
                    })}
                  </div>
                </Form.Group>
                <TapirButton
                  type={"button"}
                  text={"Lieferausnahme hinzufügen"}
                  size={"sm"}
                  icon={"calendar_add_on"}
                  variant={"outline-primary"}
                  onClick={() => onAdjustmentWeekAdd()}
                />
              </Col>
            </Row>
          </ListGroup.Item>
        </Form>
      </ListGroup>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"xl"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Vertragsperiode verwalten</h5>
      </Modal.Header>
      {getModalBody()}
      <Modal.Footer>
        <TapirButton
          text={"Speichern"}
          icon={"save"}
          variant={"primary"}
          loading={saving}
          onClick={onSave}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default GrowingPeriodModal;
