import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import { DeliveriesApi, GrowingPeriod } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import dayjs from "dayjs";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import TapirButton from "../components/TapirButton.tsx";
import { getPeriodIdFromUrl } from "./get_period_id_from_url.ts";

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
  const [growingPeriod, setGrowingPeriod] = useState<GrowingPeriod>();
  const [startDate, setStartDate] = useState<Date>();
  const [endDate, setEndDate] = useState<Date>();
  const [weeksWithoutDelivery, setWeeksWithoutDelivery] = useState<number[]>(
    [],
  );
  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDataLoading(true);

    if (!getPeriodIdFromUrl()) return;

    api
      .deliveriesGrowingPeriodsRetrieve({ id: getPeriodIdFromUrl() })
      .then((growingPeriod) => {
        setGrowingPeriod(growingPeriod);
        setStartDate(growingPeriod.startDate);
        setEndDate(growingPeriod.endDate);
        setWeeksWithoutDelivery(growingPeriod.weeksWithoutDelivery ?? []);
      })
      .catch(alert)
      .finally(() => setDataLoading(false));
  }, [show]);

  function onSave() {
    if (!growingPeriod) return;

    const form = document.getElementById(
      "growingPeriodForm",
    ) as HTMLFormElement;
    if (!form.reportValidity()) return;

    setSaving(true);
    api
      .deliveriesGrowingPeriodsUpdate({
        id: growingPeriod.id!,
        growingPeriodRequest: {
          startDate: startDate!,
          endDate: endDate!,
          weeksWithoutDelivery: weeksWithoutDelivery,
        },
      })
      .then(() => location.reload())
      .catch(alert)
      .finally(() => setSaving(false));
  }

  function onWeekChanged(index: number, newWeek: number) {
    const newWeeks = [...weeksWithoutDelivery];
    newWeeks[index] = newWeek;
    setWeeksWithoutDelivery(newWeeks);
  }

  function onAddWeek() {
    setWeeksWithoutDelivery([...weeksWithoutDelivery, 1]);
  }

  function onWeekDelete(index: number) {
    const newWeeks = [
      ...weeksWithoutDelivery.slice(0, index),
      ...weeksWithoutDelivery.slice(index + 1),
    ];
    setWeeksWithoutDelivery(newWeeks);
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Vertragsperiode verwalten</h5>
      </Modal.Header>
      <Modal.Body>
        {dataLoading || !growingPeriod ? (
          <Spinner />
        ) : (
          <>
            <Form id={"growingPeriodForm"}>
              <Form.Group className={"mb-2"}>
                <Form.Label>
                  Anfangsdatum ({formatDateNumeric(growingPeriod.startDate)})
                </Form.Label>
                <Form.Control
                  type={"date"}
                  onChange={(event) =>
                    setStartDate(new Date(event.target.value))
                  }
                  required={true}
                  value={dayjs(startDate).format("YYYY-MM-DD")}
                />
              </Form.Group>
              <Form.Group className={"mb-2"}>
                <Form.Label>
                  Enddatum ({formatDateNumeric(growingPeriod.endDate)})
                </Form.Label>
                <Form.Control
                  type={"date"}
                  onChange={(event) => setEndDate(new Date(event.target.value))}
                  required={true}
                  value={dayjs(endDate).format("YYYY-MM-DD")}
                />
              </Form.Group>
              <Form.Group>
                <Form.Label>Lieferfreie Wochen</Form.Label>
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
                            onWeekChanged(index, parseInt(event.target.value));
                          }}
                        />
                        <TapirButton
                          variant={"outline-danger"}
                          icon={"delete"}
                          size={"sm"}
                          onClick={() => onWeekDelete(index)}
                        />
                      </div>
                    );
                  })}
                </div>
                <Form.Text>Als KW</Form.Text>
              </Form.Group>
              <TapirButton
                type={"button"}
                text={"Lieferfreie Woche hinzufügen"}
                size={"sm"}
                icon={"calendar_add_on"}
                variant={"outline-primary"}
                onClick={onAddWeek}
              />
            </Form>
          </>
        )}
      </Modal.Body>
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
