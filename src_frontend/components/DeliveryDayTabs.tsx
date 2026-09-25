import React from "react";
import { Nav } from "react-bootstrap";

const WEEKDAY_NAMES = [
  "Montag",
  "Dienstag",
  "Mittwoch",
  "Donnerstag",
  "Freitag",
  "Samstag",
  "Sonntag",
];

interface DeliveryDayTabsProps {
  availableDays: number[];
  selectedDay: number | null;
  onSelectDay: (day: number | null) => void;
}

const DeliveryDayTabs: React.FC<DeliveryDayTabsProps> = ({
  availableDays,
  selectedDay,
  onSelectDay,
}) => {
  if (availableDays.length <= 1) return null;

  return (
    <div className="mb-3">
      <Nav variant="pills" className="flex-row">
        <Nav.Item>
          <Nav.Link
            active={selectedDay === null}
            onClick={() => onSelectDay(null)}
            style={{ cursor: "pointer" }}
          >
            Alle Tage
          </Nav.Link>
        </Nav.Item>
        {availableDays.map((day) => (
          <Nav.Item key={day}>
            <Nav.Link
              active={selectedDay === day}
              onClick={() => onSelectDay(day)}
              style={{ cursor: "pointer" }}
            >
              {WEEKDAY_NAMES[day]}
            </Nav.Link>
          </Nav.Item>
        ))}
      </Nav>
    </div>
  );
};

export default DeliveryDayTabs;
