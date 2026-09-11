import React from "react";
import "../../styles/bakery_styles.css";
import { currentIsoYear, isoWeeksInYear } from "../../utils/weekdays";

interface YearWeekSelectorCardProps {
  selectedYear: number;
  selectedWeek: number;
  onYearChange: (year: number) => void;
  onWeekChange: (week: number) => void;
}

const currentYear = currentIsoYear();

export const YearWeekSelectorCard: React.FC<YearWeekSelectorCardProps> = ({
  selectedYear,
  selectedWeek,
  onYearChange,
  onWeekChange,
}) => {
  const years = Array.from(
    { length: currentYear + 1 - 2026 + 1 },
    (_, i) => 2026 + i,
  );
  const weeksInSelectedYear = isoWeeksInYear(selectedYear);

  // 2026 has 53 ISO weeks, 2027 has 52. Leaving KW 53 selected while switching
  // to 2027 asked the backend for a week that does not exist.
  const handleYearChange = (year: number) => {
    onYearChange(year);
    const weeksInNewYear = isoWeeksInYear(year);
    if (selectedWeek > weeksInNewYear) {
      onWeekChange(weeksInNewYear);
    }
  };

  return (
    <div className="card shadow-sm">
      <div className="card-header header-darkbrown-on-sahara">
        <h5 className="mb-0">Woche & Jahr auswählen</h5>
      </div>
      <div className="card-body small">
        <div className="row g-3">
          <div className="col-md-1">
            <select
              className="form-select"
              value={selectedYear}
              onChange={(e) => handleYearChange(Number(e.target.value))}
            >
              {years.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-2" style={{ flex: "0 0 10%" }}>
            <select
              className="form-select"
              value={selectedWeek}
              onChange={(e) => onWeekChange(Number(e.target.value))}
            >
              {Array.from({ length: weeksInSelectedYear }, (_, i) => i + 1).map(
                (week) => (
                  <option key={week} value={week}>
                    KW {week}
                  </option>
                ),
              )}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};
