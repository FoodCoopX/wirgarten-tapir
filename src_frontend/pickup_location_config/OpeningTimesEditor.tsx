import React from "react";
import { Form } from "react-bootstrap";
import { DayOfWeekEnum } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { OpeningTimeRow, WEEKDAYS } from "./pickupLocationForm.ts";

function buildFollowingOpeningTime(
  openingTime: OpeningTimeRow | undefined,
): OpeningTimeRow {
  if (openingTime === undefined) {
    return { dayOfWeek: 0, openTime: "", closeTime: "" };
  }
  return {
    ...openingTime,
    dayOfWeek: ((openingTime.dayOfWeek + 1) % 7) as DayOfWeekEnum,
  };
}

interface OpeningTimesEditorProps {
  openingTimes: OpeningTimeRow[];
  onChange: (openingTimes: OpeningTimeRow[]) => void;
  error?: string;
}

const OpeningTimesEditor: React.FC<OpeningTimesEditorProps> = ({
  openingTimes,
  onChange,
  error,
}) => {
  function updateOpeningTime(index: number, changes: Partial<OpeningTimeRow>) {
    onChange(
      openingTimes.map((openingTime, currentIndex) =>
        currentIndex === index ? { ...openingTime, ...changes } : openingTime,
      ),
    );
  }

  function duplicateOpeningTime(index: number) {
    onChange([
      ...openingTimes.slice(0, index + 1),
      buildFollowingOpeningTime(openingTimes[index]),
      ...openingTimes.slice(index + 1),
    ]);
  }

  function removeOpeningTime(index: number) {
    onChange(openingTimes.filter((_, currentIndex) => currentIndex !== index));
  }

  return (
    <>
      {openingTimes.map((openingTime, index) => (
        <div className={"d-flex gap-2 mb-2 align-items-center"} key={index}>
          <Form.Select
            value={openingTime.dayOfWeek}
            onChange={(event) =>
              updateOpeningTime(index, {
                dayOfWeek: Number(event.target.value) as DayOfWeekEnum,
              })
            }
          >
            {WEEKDAYS.map((weekday, dayOfWeek) => (
              <option key={dayOfWeek} value={dayOfWeek}>
                {weekday}
              </option>
            ))}
          </Form.Select>
          <Form.Control
            type={"time"}
            required={true}
            value={openingTime.openTime}
            onChange={(event) =>
              updateOpeningTime(index, { openTime: event.target.value })
            }
          />
          <span>–</span>
          <Form.Control
            type={"time"}
            required={true}
            value={openingTime.closeTime}
            onChange={(event) =>
              updateOpeningTime(index, { closeTime: event.target.value })
            }
          />
          <TapirButton
            variant={"outline-secondary"}
            icon={"content_copy"}
            size={"sm"}
            tooltip={"Für den nächsten Tag kopieren"}
            onClick={() => duplicateOpeningTime(index)}
          />
          <TapirButton
            variant={"outline-danger"}
            icon={"delete"}
            size={"sm"}
            onClick={() => removeOpeningTime(index)}
          />
        </div>
      ))}
      {error && (
        <div className={"invalid-message text-danger small mb-2"}>{error}</div>
      )}
      <TapirButton
        variant={"outline-primary"}
        icon={"add"}
        size={"sm"}
        text={"Abholzeit hinzufügen"}
        onClick={() =>
          onChange([
            ...openingTimes,
            buildFollowingOpeningTime(openingTimes.at(-1)),
          ])
        }
      />
    </>
  );
};

export default OpeningTimesEditor;
