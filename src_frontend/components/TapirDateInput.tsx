import dayjs from "dayjs";
import React, { useEffect, useState } from "react";
import { Form } from "react-bootstrap";

interface TapirDateInputProps {
  date: Date;
  setDate: React.Dispatch<React.SetStateAction<Date>>;
  showValidation?: boolean;
}

const TapirDateInput: React.FC<TapirDateInputProps> = ({
  date,
  setDate,
  showValidation,
}) => {
  const [intervalValue, setIntervalValue] = useState(
    dayjs(date).format("YYYY-MM-DD"),
  );

  useEffect(() => {
    const date = dayjs(intervalValue);
    if (date.isValid()) {
      // We must specify UTC otherwise the server will convert
      // local time to UTC and create the share one day too early.
      setDate(new Date(Date.UTC(date.year(), date.month(), date.date())));
    }
  }, [intervalValue]);

  return (
    <Form.Control
      type={"date"}
      onChange={(event) => setIntervalValue(event.target.value)}
      value={intervalValue}
      isValid={showValidation && dayjs(intervalValue).isValid()}
      isInvalid={showValidation && !dayjs(intervalValue).isValid()}
    />
  );
};

export default TapirDateInput;
