import dayjs from "dayjs";
import "dayjs/locale/de";
import WeekOfYear from "dayjs/plugin/weekOfYear";
import React, { useEffect, useState } from "react";
import { Form, Spinner } from "react-bootstrap";
import {
  SubscriptionsApiConvertWeekToDateForSubscriptionChangeRetrieveBoundaryEnum as Boundary,
  SubscriptionDetails,
  SubscriptionsApi,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { fromApiDate } from "../utils/apiDate.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { formatDateTextLong } from "../utils/formatDateTextLong.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

dayjs.extend(WeekOfYear);
dayjs.locale("de");

interface SubscriptionChangeDatePickerProps {
  subscriptionId: string;
  subscription: SubscriptionDetails;
  boundary: Boundary;
  onChange: (date: Date | undefined) => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

function isWeekValid(week: number | undefined): week is number {
  return (
    week !== undefined && Number.isInteger(week) && week >= 1 && week <= 53
  );
}

const SubscriptionChangeDatePicker: React.FC<
  SubscriptionChangeDatePickerProps
> = ({ subscriptionId, subscription, boundary, onChange, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi);
  const isStart = boundary === Boundary.Start;
  const currentDate = isStart ? subscription.startDate : subscription.endDate;
  const periodBoundaryDate = isStart
    ? subscription.growingPeriodStartDate
    : subscription.growingPeriodEndDate;

  const [isPeriodBoundary, setIsPeriodBoundary] = useState(
    currentDate === periodBoundaryDate,
  );
  const [week, setWeek] = useState<number | undefined>(
    currentDate === periodBoundaryDate ? undefined : dayjs(currentDate).week(),
  );
  const [weekDate, setWeekDate] = useState<Date>();
  const [weekError, setWeekError] = useState<string>();

  useEffect(() => {
    setWeekDate(undefined);
    setWeekError(undefined);
    if (isPeriodBoundary) {
      onChange(fromApiDate(periodBoundaryDate));
      return;
    }
    onChange(undefined);
    if (!isWeekValid(week)) {
      return;
    }

    let cancelled = false;
    subscriptionsApi
      .subscriptionsApiConvertWeekToDateForSubscriptionChangeRetrieve({
        subscriptionId: subscriptionId,
        week: week,
        boundary: boundary,
      })
      .then((response) => {
        if (cancelled) return;
        if (response.error || !response.date) {
          setWeekError(response.error ?? undefined);
          return;
        }
        const date = fromApiDate(response.date);
        setWeekDate(date);
        onChange(date);
      })
      .catch((error) => {
        if (cancelled) return;
        handleRequestError(
          error,
          "Fehler beim Laden des Datums",
          setToastDatas,
        );
      });

    return () => {
      cancelled = true;
    };
  }, [week, isPeriodBoundary]);

  function getWeekDateDisplay() {
    if (!isWeekValid(week) || weekError) {
      return null;
    }
    return weekDate ? formatDateTextLong(weekDate) : <Spinner size={"sm"} />;
  }

  return (
    <>
      <Form.Select
        value={isPeriodBoundary ? "period_boundary" : "week"}
        onChange={(event) =>
          setIsPeriodBoundary(event.target.value === "period_boundary")
        }
        className={"mb-2"}
        style={{ width: "auto" }}
      >
        <option value={"period_boundary"}>
          {isStart ? "Am ersten" : "Am letzten"} Tag der Vertragsperiode (
          {formatDateNumeric(periodBoundaryDate)})
        </option>
        <option value={"week"}>In einer bestimmten KW</option>
      </Form.Select>
      {!isPeriodBoundary && (
        <>
          <span className={"d-flex flex-row gap-2 align-items-center"}>
            <span>KW</span>
            <Form.Control
              type={"number"}
              min={1}
              max={53}
              step={1}
              value={week ?? ""}
              onChange={(event) => {
                const value = Number.parseInt(event.target.value);
                setWeek(Number.isNaN(value) ? undefined : value);
              }}
              style={{ width: "90px" }}
              isInvalid={
                (week !== undefined && !isWeekValid(week)) ||
                weekError !== undefined
              }
            />
            {getWeekDateDisplay()}
          </span>
          {weekError && (
            <Form.Text className={"text-danger"}>{weekError}</Form.Text>
          )}
        </>
      )}
    </>
  );
};

export default SubscriptionChangeDatePicker;
