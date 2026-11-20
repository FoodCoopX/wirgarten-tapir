import dayjs from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";
import React, { useState } from "react";
import { Form } from "react-bootstrap";
import {
  AdminSizeChangeDateOption,
  AdminSizeChangeWeekOption,
} from "../api-client";
import { fromApiDate } from "../utils/apiDate.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

dayjs.extend(isoWeek);

type DateOptionKind = "next_possible_start" | "week" | "next_period_start";

interface SubscriptionStartDateOptionsProps {
  nextPossibleStart: AdminSizeChangeDateOption;
  weeks: AdminSizeChangeWeekOption[];
  nextPeriodStart: AdminSizeChangeDateOption;
  selectedDate: string | undefined;
  setSelectedDate: (date: string | undefined) => void;
}

function getIsoYear(week: AdminSizeChangeWeekOption): number {
  return dayjs(fromApiDate(week.date)).isoWeekYear();
}

function formatWeek(week: AdminSizeChangeWeekOption): string {
  const weekNumber = dayjs(fromApiDate(week.date)).isoWeek();
  let result = `KW ${weekNumber} · ${formatDateNumeric(week.date)}`;
  if (week.isBeforeNextPossibleStart) {
    result += " (Pufferzeit ignoriert)";
  }
  if (week.hasNoDelivery) {
    result += " (keine Lieferung)";
  }
  return result;
}

const SubscriptionStartDateOptions: React.FC<
  SubscriptionStartDateOptionsProps
> = ({
  nextPossibleStart,
  weeks,
  nextPeriodStart,
  selectedDate,
  setSelectedDate,
}) => {
  const [kind, setKind] = useState<DateOptionKind | undefined>(() => {
    if (selectedDate === undefined) return undefined;
    if (selectedDate === nextPossibleStart.date) return "next_possible_start";
    if (selectedDate === nextPeriodStart.date) return "next_period_start";
    return "week";
  });
  const years = [...new Set(weeks.map(getIsoYear))];

  function selectKind(newKind: DateOptionKind) {
    setKind(newKind);
    switch (newKind) {
      case "next_possible_start":
        setSelectedDate(nextPossibleStart.date ?? undefined);
        break;
      case "week":
        setSelectedDate(undefined);
        break;
      case "next_period_start":
        setSelectedDate(nextPeriodStart.date ?? undefined);
        break;
    }
  }

  function buildDisabledReason(option: AdminSizeChangeDateOption) {
    if (option.date === null) {
      return "Es gibt keine folgende Vertragsperiode.";
    }
    if (!option.enabled) {
      return "Das Datum liegt außerhalb der Vertragslaufzeit.";
    }
    return undefined;
  }

  function buildOptionLabel(label: string, option: AdminSizeChangeDateOption) {
    const disabledReason = buildDisabledReason(option);
    return (
      <>
        {label}
        {option.date !== null && ` (${formatDateNumeric(option.date)})`}
        {disabledReason && (
          <div className={"text-muted small"}>{disabledReason}</div>
        )}
      </>
    );
  }

  return (
    <div className={"d-flex flex-column gap-2"}>
      <Form.Check
        type={"radio"}
        id={"start_date_next_possible_start"}
        checked={kind === "next_possible_start"}
        disabled={!nextPossibleStart.enabled || nextPossibleStart.date === null}
        onChange={() => selectKind("next_possible_start")}
        label={buildOptionLabel("Nächstmöglicher Beginn", nextPossibleStart)}
      />
      <Form.Check
        type={"radio"}
        id={"start_date_week"}
        checked={kind === "week"}
        disabled={weeks.length === 0}
        onChange={() => selectKind("week")}
        label={
          <>
            In einer bestimmten KW
            {weeks.length === 0 && (
              <div className={"text-muted small"}>
                Innerhalb der Vertragslaufzeit liegt keine Woche ab heute.
              </div>
            )}
          </>
        }
      />
      {kind === "week" && (
        <div className={"ps-4"}>
          <Form.Select
            value={selectedDate ?? ""}
            onChange={(event) =>
              setSelectedDate(event.target.value || undefined)
            }
          >
            <option value={""}>Woche auswählen</option>
            {years.map((year) => (
              <optgroup key={year} label={String(year)}>
                {weeks
                  .filter((week) => getIsoYear(week) === year)
                  .map((week) => (
                    <option key={week.date} value={week.date}>
                      {formatWeek(week)}
                    </option>
                  ))}
              </optgroup>
            ))}
          </Form.Select>
        </div>
      )}
      <Form.Check
        type={"radio"}
        id={"start_date_next_period_start"}
        checked={kind === "next_period_start"}
        disabled={!nextPeriodStart.enabled || nextPeriodStart.date === null}
        onChange={() => selectKind("next_period_start")}
        label={buildOptionLabel(
          "Beginn der nächsten Vertragsperiode",
          nextPeriodStart,
        )}
      />
    </div>
  );
};

export default SubscriptionStartDateOptions;
