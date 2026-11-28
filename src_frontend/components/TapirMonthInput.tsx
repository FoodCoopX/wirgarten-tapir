import React from "react";
import { Form } from "react-bootstrap";

export interface YearAndMonth {
  year: number;
  // 0 = January, like Date.getMonth()
  month: number;
}

interface TapirMonthInputProps {
  value: YearAndMonth;
  onChange: (value: YearAndMonth) => void;
  ariaLabel: string;
  disabled?: boolean;
}

function getMonthDisplay(month: number) {
  return new Date(2000, month, 1).toLocaleDateString("de-DE", {
    month: "long",
  });
}

const TapirMonthInput: React.FC<TapirMonthInputProps> = ({
  value,
  onChange,
  ariaLabel,
  disabled,
}) => {
  return (
    <div className={"d-flex flex-row gap-2"}>
      <Form.Select
        aria-label={`${ariaLabel}: Monat`}
        value={value.month}
        disabled={disabled}
        onChange={(event) =>
          onChange({ ...value, month: Number.parseInt(event.target.value) })
        }
      >
        {Array.from(new Array(12).keys()).map((month) => (
          <option key={month} value={month}>
            {getMonthDisplay(month)}
          </option>
        ))}
      </Form.Select>
      <Form.Control
        aria-label={`${ariaLabel}: Jahr`}
        type={"number"}
        step={1}
        min={2000}
        max={2100}
        style={{ maxWidth: "8rem" }}
        value={Number.isNaN(value.year) ? "" : value.year}
        disabled={disabled}
        onChange={(event) =>
          onChange({ ...value, year: Number.parseInt(event.target.value) })
        }
      />
    </div>
  );
};

export default TapirMonthInput;
