import React, { useEffect, useState } from "react";
import { Form } from "react-bootstrap";
import dayjs from "dayjs";

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
      setDate(date.toDate());
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
