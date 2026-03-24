import dayjs from 'dayjs';
import React from 'react';
import '../../styles/bakery_styles.css';

interface YearWeekSelectorCardProps {
  selectedYear: number;
  selectedWeek: number;
  onYearChange: (year: number) => void;
  onWeekChange: (week: number) => void;
}

const currentYear = dayjs().year();

export const YearWeekSelectorCard: React.FC<YearWeekSelectorCardProps> = ({
  selectedYear,
  selectedWeek,
  onYearChange,
  onWeekChange,
}) => {

const years = Array.from({ length: (currentYear + 1) - 2026 + 1 }, (_, i) => 2026 + i);

  return (
    <div className="card shadow-sm">
      <div className="card-header header-darkbrown-on-sahara">
        <h5 className="mb-0">
          Woche & Jahr auswählen
        </h5>
      </div>
      <div className="card-body small">
        <div className="row g-3">
          <div className="col-md-1">
      
            <select
              className="form-select"
              value={selectedYear}
              onChange={(e) => onYearChange(Number(e.target.value))}
              
            >
              {years.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div className="col-md-2" style={{ flex: '0 0 10%' }}>          
            <select
              className="form-select"
              value={selectedWeek}
              onChange={(e) => onWeekChange(Number(e.target.value))}
            >
              {Array.from({ length: 53 }, (_, i) => i + 1).map(week => (
                <option key={week} value={week}>KW {week}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};