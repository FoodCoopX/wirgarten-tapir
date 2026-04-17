import React, { useState, useEffect } from 'react';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import '../../styles/bakery_styles.css';

interface BreadStat {
  breadName: string;
  count: number;
  percentage: number;
}

interface PreferredBreadStats {
  totalMembers: number;
  membersWithPreferences: number;
  membersWithoutPreferences: number;
  breads: BreadStat[];
}

interface PreferredBreadStatisticsCardProps {
  year: number;
  week: number;
  deliveryDay: number;
  csrfToken: string;
}

export const PreferredBreadStatisticsCard: React.FC<PreferredBreadStatisticsCardProps> = ({
  year, week, deliveryDay, csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [stats, setStats] = useState<PreferredBreadStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, [year, week, deliveryDay]);

  const loadStats = () => {
    setLoading(true);
    setError(null);
    fetch(
      `/bakery/api/preferred-bread-statistics/?year=${year}&delivery_week=${week}&delivery_day=${deliveryDay}`,
      {
        headers: { 'X-CSRFToken': csrfToken },
        credentials: 'same-origin',
      }
    )
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setStats({
          totalMembers: data.total_members,
          membersWithPreferences: data.members_with_preferences,
          membersWithoutPreferences: data.members_without_preferences,
          breads: (data.breads || []).map((b: any) => ({
            breadName: b.bread_name,
            count: b.count,
            percentage: b.percentage,
          })),
        });
      })
      .catch((e: any) => {
        setError(e.message || 'Fehler beim Laden');
      })
      .finally(() => {
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
      <div className="alert alert-danger py-1 px-2" style={{ fontSize: '0.75rem' }}>
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
  const prefPercent = stats.totalMembers > 0
    ? Math.round(stats.membersWithPreferences / stats.totalMembers * 100)
    : 0;

  return (
    <div>
      {/* Summary badges */}
      <div className="d-flex flex-wrap gap-2 mb-3">
        <span className="badge badge-bakery-primary" style={{ fontSize: '0.75rem' }}>
          <span className="material-icons me-1" style={{ fontSize: '12px', verticalAlign: 'middle' }}>people</span>
          {stats.totalMembers} Mitglieder
        </span>
        <span className="badge bg-success" style={{ fontSize: '0.75rem' }}>
          <span className="material-icons me-1" style={{ fontSize: '12px', verticalAlign: 'middle' }}>favorite</span>
          {stats.membersWithPreferences} mit Präferenz ({prefPercent}%)
        </span>
        <span className="badge bg-secondary" style={{ fontSize: '0.75rem' }}>
          <span className="material-icons me-1" style={{ fontSize: '12px', verticalAlign: 'middle' }}>help_outline</span>
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
                  <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>{bread.breadName}</span>
                  <span className="text-bakery-primary-darker" style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>
                    {bread.count}× ({bread.percentage}%)
                  </span>
                </div>
                <div className="progress-bar-bakery-chart" style={{ borderRadius: '4px', height: '12px', overflow: 'hidden' }}>
                  <div
                    className="progress-bar-bakery-primary"
                    style={{
                      width: `${barWidth}%`,
                      height: '100%',
                      borderRadius: '4px',
                      transition: 'width 0.5s ease',
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