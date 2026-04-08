import "dayjs/locale/de";
import React from "react";
import { Form, Spinner } from "react-bootstrap";
import { formatDateTextLong } from "../utils/formatDateTextLong.ts";

interface SubscriptionChangeDatesWeekInputProps {
  week: number | undefined;
  setWeek: (value: number) => void;
  date: Date | undefined;
}

const SubscriptionChangeDatesWeekInput: React.FC<
  SubscriptionChangeDatesWeekInputProps
> = ({ week, setWeek, date }) => {
  function getDateDisplay() {
    if (week && date) {
      return formatDateTextLong(date);
    }

    return <Spinner size={"sm"} />;
  }

  return (
    <span className={"d-flex flex-row gap-2 align-items-center"}>
      <span>KW</span>
      <Form.Control
        type={"number"}
        min={1}
        max={53}
        step={1}
        value={week}
        onChange={(event) => {
          setWeek(Number.parseInt(event.target.value));
        }}
        style={{ width: "90px" }}
        isInvalid={week !== undefined && (week < 1 || week > 53)}
      />
      {getDateDisplay()}
    </span>
  );
};

export default SubscriptionChangeDatesWeekInput;
