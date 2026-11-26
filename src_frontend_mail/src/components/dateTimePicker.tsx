import {
  DateTime,
  loadLocale,
  locale,
  TempusDominus,
} from "@eonasdan/tempus-dominus";
import "@eonasdan/tempus-dominus/dist/css/tempus-dominus.min.css";
import { localization, name } from "@eonasdan/tempus-dominus/dist/locales/de";
import { ChangeEvent } from "@eonasdan/tempus-dominus/types/utilities/event-types";
import "@fortawesome/fontawesome-free/css/fontawesome.css";
import "@fortawesome/fontawesome-free/css/solid.css";
import React, { useEffect, useRef } from "react";

interface DateTimePickerProps {
  onChange: (value?: Date) => void;
  initialValue: Date;
  minDate?: Date;
  maxDate?: Date;
}

const DateTimePicker: React.FC<DateTimePickerProps> = ({
  onChange,
  initialValue,
  minDate,
  maxDate,
}) => {
  const pickerRef = useRef<HTMLDivElement>(null);
  let dateTimePicker: TempusDominus | null = null;

  useEffect(() => {
    if (!pickerRef.current) return;
    loadLocale({ localization, name });
    locale(name);
    const currentYear = new Date().getFullYear();
    dateTimePicker = new TempusDominus(pickerRef.current, {
      display: { theme: "light" },
      restrictions: {
        minDate: DateTime.convert(minDate ?? new Date(currentYear, 0, 1)),
        maxDate: DateTime.convert(maxDate ?? new Date(currentYear + 5, 11, 31)),
      },
    });
    dateTimePicker.subscribe("change.td", (e: ChangeEvent) => {
      onChange(e.date);
    });
  }, [pickerRef]);

  useEffect(() => {
    if (!dateTimePicker) return;
    dateTimePicker.dates.setValue(
      dateTimePicker.dates.parseInput(initialValue),
    );
  }, [initialValue, dateTimePicker]);

  return (
    <div id="htmlTarget">
      <div ref={pickerRef} className="input-group">
        <input type="text" className="form-control" />
        <span className="input-group-text">
          <i className="fas fa-calendar"></i>
        </span>
      </div>
    </div>
  );
};

export default DateTimePicker;
