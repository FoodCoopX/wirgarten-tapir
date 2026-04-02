import React, { useEffect, useState } from "react";
import { Alert, Form, Spinner } from "react-bootstrap";
import { DeliveriesApi, GrowingPeriod } from "../api-client";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { CustomCycleDeliveryWeeks } from "../types/CustomCycleDeliveryWeeks.ts";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import TapirHelpButton from "../components/TapirHelpButton.tsx";

interface CustomCycleDeliveryWeeksInputProps {
  deliveryWeeks: CustomCycleDeliveryWeeks;
  setDeliveryWeeks: (weeks: CustomCycleDeliveryWeeks) => void;
  allGrowingPeriods: GrowingPeriod[];
}

const CustomCycleDeliveryWeeksInput: React.FC<
  CustomCycleDeliveryWeeksInputProps
> = ({ deliveryWeeks, setDeliveryWeeks, allGrowingPeriods }) => {
  const deliveriesApi = useApi(DeliveriesApi, getCsrfToken());
  const [selectedGrowingPeriod, setSelectedGrowingPeriod] =
    useState<GrowingPeriod>();
  const [abortController, setAbortController] = useState<AbortController>();
  const [deliveryDates, setDeliveryDates] = useState<{
    [key: string]: { [key: string]: Date };
  }>({});
  const [internalWeeks, setInternalWeeks] = useState<{
    [growingPeriodId: string]: string[];
  }>({});
  const [errorMessage, setErrorMessage] = useState("");
  const [initialValueSet, setInitialValueSet] = useState(false);

  useEffect(() => {
    if (allGrowingPeriods.length === 0) {
      return;
    }

    const today = new Date();
    for (const growingPeriod of allGrowingPeriods) {
      if (growingPeriod.startDate <= today && today <= growingPeriod.endDate) {
        setSelectedGrowingPeriod(growingPeriod);
        return;
      }
    }

    setSelectedGrowingPeriod(allGrowingPeriods.at(-1));
  }, [allGrowingPeriods]);

  useEffect(() => {
    if (!areAllInternalWeeksValid()) {
      return;
    }

    const newDeliveryWeeks: CustomCycleDeliveryWeeks = {};

    for (const [growingPeriodId, weeksAsString] of Object.entries(
      internalWeeks,
    )) {
      newDeliveryWeeks[growingPeriodId] = [];
      for (const weekAsString of weeksAsString) {
        newDeliveryWeeks[growingPeriodId].push(Number.parseInt(weekAsString));
      }
    }
    setDeliveryWeeks(newDeliveryWeeks);
  }, [internalWeeks]);

  useEffect(() => {
    if (abortController) {
      abortController.abort();
    }

    const localController = new AbortController();
    setAbortController(localController);

    deliveriesApi
      .deliveriesApiGetDatesFromCustomCycleDeliveryWeeksCreate(
        {
          customCycleDeliveryWeeksRequest: {
            customCycleDeliveryWeeks: deliveryWeeks,
          },
        },
        { signal: localController.signal },
      )
      .then((response) => {
        setErrorMessage(response.error);
        if (response.error.length > 0) {
          setDeliveryDates({});
        } else {
          setDeliveryDates(response.customCycleDeliveryWeeksDates);
        }
      })
      .catch(async (error) => {
        if (error.cause?.name === "AbortError") return;
        await handleRequestError(
          error,
          "Fehler beim Laden der Lieferung-Daten",
        );
      });
  }, [deliveryWeeks]);

  useEffect(() => {
    if (initialValueSet || Object.keys(deliveryWeeks).length == 0) {
      return;
    }

    const newInternalWeeks: {
      [growingPeriodId: string]: string[];
    } = {};

    for (const [growingPeriodId, weeksAsNumber] of Object.entries(
      deliveryWeeks,
    )) {
      newInternalWeeks[growingPeriodId] = [];
      for (const weekAsNumber of weeksAsNumber) {
        newInternalWeeks[growingPeriodId].push(weekAsNumber.toString());
      }
    }
    setInternalWeeks(newInternalWeeks);
    setInitialValueSet(true);
  }, [deliveryWeeks]);

  function getGrowingPeriodById(id: string) {
    return allGrowingPeriods.find((growingPeriod) => growingPeriod.id == id);
  }

  function getInternalWeeksForCurrentPeriod() {
    return internalWeeks[selectedGrowingPeriod?.id ?? ""] ?? [];
  }

  function updateDeliveryWeeks(
    growingPeriod: GrowingPeriod,
    index: number,
    newValue: string,
  ) {
    internalWeeks[growingPeriod.id!][index] = newValue;
    setInternalWeeks({ ...internalWeeks });
  }

  function areAllInternalWeeksValid() {
    for (const weeks of Object.values(internalWeeks)) {
      for (const weekAsString of weeks) {
        const weekAsInt = Number.parseInt(weekAsString);
        if (Number.isNaN(weekAsInt)) {
          return false;
        }
      }
    }
    return true;
  }

  function addDelivery() {
    const periodId = selectedGrowingPeriod!.id!;
    if (!(periodId in internalWeeks)) {
      internalWeeks[periodId] = [];
    }
    internalWeeks[periodId].push("1");
    setInternalWeeks({ ...internalWeeks });
  }

  function deleteDelivery(indexToRemove: number) {
    const periodId = selectedGrowingPeriod!.id!;
    internalWeeks[periodId] = internalWeeks[periodId].filter(
      (_, index) => index !== indexToRemove,
    );
    setInternalWeeks({ ...internalWeeks });
  }

  function getStartDateForWeek(week: number) {
    const periodId = selectedGrowingPeriod?.id ?? "";
    if (!(periodId in deliveryDates) || !(week in deliveryDates[periodId])) {
      return undefined;
    }
    return new Date(deliveryDates[periodId][week]);
  }

  function getDateDisplay(week: number) {
    const startOfWeek = getStartDateForWeek(week);
    if (!startOfWeek) {
      return <Spinner />;
    }
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(endOfWeek.getDate() + 6);

    const formatter = new Intl.DateTimeFormat("de-DE", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });

    return formatter.formatRange(startOfWeek, endOfWeek);
  }

  return (
    <div className={"d-flex flex-column gap-2"}>
      <Form.Group controlId={"delivery_cycle"}>
        <Form.Label>Vertragsperiode</Form.Label>
        <Form.Select
          onChange={(event) =>
            setSelectedGrowingPeriod(getGrowingPeriodById(event.target.value))
          }
          value={selectedGrowingPeriod?.id}
        >
          {allGrowingPeriods.map((growingPeriod) => {
            return (
              <option key={growingPeriod.id} value={growingPeriod.id}>
                {formatDateNumeric(growingPeriod.startDate)} -{" "}
                {formatDateNumeric(growingPeriod.endDate)}
              </option>
            );
          })}
        </Form.Select>
      </Form.Group>
      <div className={"d-flex flex-row gap-2 align-items-center"}>
        <span>Lieferwochen für dieses Produkt</span>
        <TapirHelpButton
          text={
            "Bitte gib an, in welchen Wochen das Produkt abgeholt bzw. geliefert wird. Du kannst beliebig viele Wochen angeben und auch wieder löschen. Änderungen können für zukünftige Abholungen / Lieferungen vorgenommen werden."
          }
          buttonSize={"sm"}
        />
      </div>
      {getInternalWeeksForCurrentPeriod().map((week, index) => (
        <Form.Group
          key={index}
          className={"d-flex flex-row gap-2 align-items-center"}
        >
          <Form.Label className={"mb-0"}>KW</Form.Label>
          <Form.Control
            onChange={(event) =>
              updateDeliveryWeeks(
                selectedGrowingPeriod!,
                index,
                event.target.value,
              )
            }
            value={week}
            style={{ width: "50px" }}
          />
          <div style={{ width: "170px" }}>
            {getDateDisplay(Number.parseInt(week))}
          </div>
          <TapirButton
            variant={"outline-danger"}
            icon={"delete"}
            onClick={() => deleteDelivery(index)}
            size={"sm"}
          />
        </Form.Group>
      ))}
      <TapirButton
        text={"Lieferung hinzufügen"}
        variant={"outline-secondary"}
        icon={"add_circle"}
        onClick={addDelivery}
        size={"sm"}
      />
      {errorMessage.length > 0 && (
        <Alert variant={"warning"}>
          Fehler beim Berechnen der Daten: {errorMessage}
        </Alert>
      )}
    </div>
  );
};

export default CustomCycleDeliveryWeeksInput;
