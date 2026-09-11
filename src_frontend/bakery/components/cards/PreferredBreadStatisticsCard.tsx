import React, { useEffect, useRef, useState } from "react";
import { BakeryApi } from "../../../api-client";
import type { PreferredBreadStatistics } from "../../../api-client/models";
import { useApi } from "../../../hooks/useApi";
import "../../styles/bakery_styles.css";

interface PreferredBreadStatisticsCardProps {
  year: number;
  week: number;
  deliveryDay: number;
  csrfToken: string;
}

export const PreferredBreadStatisticsCard: React.FC<
  PreferredBreadStatisticsCardProps
> = ({ year, week, deliveryDay, csrfToken }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [stats, setStats] = useState<PreferredBreadStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Same guard as the other week-scoped cards: a response for a week the
  // user has already left must not repaint this one.
  const selectionRef = useRef(`${year}/${week}/${deliveryDay}`);

  useEffect(() => {
    selectionRef.current = `${year}/${week}/${deliveryDay}`;
    loadStats();
  }, [year, week, deliveryDay]);

  // Through the generated client: this was the frontend's only hand-written
  // fetch(), hand-mapping snake_case keys the schema now declares, while the
  // `bakeryApi` it had already built sat unused.
  const loadStats = () => {
    const requestedFor = `${year}/${week}/${deliveryDay}`;
    setLoading(true);
    setError(null);
    bakeryApi
      .bakeryApiPreferredBreadStatisticsRetrieve({
        year,
        deliveryWeek: week,
        deliveryDay,
      })
      .then((data) => {
        if (selectionRef.current !== requestedFor) return;
        setStats(data);
      })
      .catch((e: unknown) => {
        if (selectionRef.current !== requestedFor) return;
        setError(e instanceof Error ? e.message : "Fehler beim Laden");
      })
      .finally(() => {
        if (selectionRef.current !== requestedFor) return;
        setLoading(false);
      });
  };

  if (loading) {
    return (
      <div className="text-center py-3">
        <div className="spinner-border spinner-border-sm spinner-bakery-primary" />
        <p className="mt-1 text-muted small">Lade Statistik...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="alert alert-danger py-1 px-2"
        style={{ fontSize: "0.75rem" }}
      >
        Fehler: {error}
      </div>
    );
  }

  if (!stats || stats.totalMembers === 0) {
    return (
      <p className="text-muted small text-center py-2">
        Keine Mitglieder mit Brotlieferungen.
      </p>
    );
  }

  const maxCount = stats.breads.length > 0 ? stats.breads[0].count : 1;
  const prefPercent =
    stats.totalMembers > 0
      ? Math.round((stats.membersWithPreferences / stats.totalMembers) * 100)
      : 0;

  return (
    <div>
      {/* Summary badges */}
      <div className="d-flex flex-wrap gap-2 mb-3">
        <span
          className="badge badge-bakery-primary"
          style={{ fontSize: "0.75rem" }}
        >
          <span
            className="material-icons me-1"
            style={{ fontSize: "12px", verticalAlign: "middle" }}
          >
            people
          </span>
          {stats.totalMembers} Mitglieder
        </span>
        <span className="badge bg-success" style={{ fontSize: "0.75rem" }}>
          <span
            className="material-icons me-1"
            style={{ fontSize: "12px", verticalAlign: "middle" }}
          >
            favorite
          </span>
          {stats.membersWithPreferences} mit Präferenz ({prefPercent}%)
        </span>
        <span className="badge bg-secondary" style={{ fontSize: "0.75rem" }}>
          <span
            className="material-icons me-1"
            style={{ fontSize: "12px", verticalAlign: "middle" }}
          >
            help_outline
          </span>
          {stats.membersWithoutPreferences} ohne
        </span>
      </div>

      {/* Bar chart */}
      {stats.breads.length > 0 ? (
        <div className="d-flex flex-column gap-2">
          {stats.breads.map((bread) => {
            const barWidth = Math.max(5, (bread.count / maxCount) * 100);
            return (
              <div key={bread.breadName}>
                <div className="d-flex justify-content-between align-items-center mb-1">
                  <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>
                    {bread.breadName}
                  </span>
                  <span
                    className="text-bakery-primary-darker"
                    style={{ fontSize: "0.75rem", fontWeight: "bold" }}
                  >
                    {bread.count}× ({bread.percentage}%)
                  </span>
                </div>
                <div
                  className="progress-bar-bakery-chart"
                  style={{
                    borderRadius: "4px",
                    height: "12px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    className="progress-bar-bakery-primary"
                    style={{
                      width: `${barWidth}%`,
                      height: "100%",
                      borderRadius: "4px",
                      transition: "width 0.5s ease",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-muted small text-center">
          Noch keine Brotpräferenzen hinterlegt.
        </p>
      )}
    </div>
  );
};
