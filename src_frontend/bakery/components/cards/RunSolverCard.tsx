import React, { useState } from 'react';
import { Lightning, CheckCircleFill, ExclamationTriangleFill, InfoCircleFill, XCircleFill } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type {
  SolverPreviewResponse,
  SolverPreviewDetailResponse,
} from '../../../api-client/models';

interface SolverDiagnostic {
  level: 'info' | 'warning' | 'error';
  category: string;
  breadName?: string | null;
  locationName?: string | null;
  message: string;
}

interface RunSolverCardProps {
  year: number;
  deliveryWeek: number;
  deliveryDay: number;
  csrfToken: string;
  hasSavedPlan?: boolean;
  onPreviewDetail?: (detail: SolverPreviewDetailResponse) => void;
  onApplied?: () => void;
}

const DiagnosticIcon: React.FC<{ level: string }> = ({ level }) => {
  switch (level) {
    case 'error':
      return <XCircleFill className="text-danger me-1" />;
    case 'warning':
      return <ExclamationTriangleFill className="text-warning me-1" />;
    default:
      return <InfoCircleFill className="text-info me-1" />;
  }
};

const DiagnosticsList: React.FC<{ diagnostics: SolverDiagnostic[] }> = ({ diagnostics }) => {
  if (!diagnostics || diagnostics.length === 0) return null;

  const errors = diagnostics.filter(d => d.level === 'error');
  const warnings = diagnostics.filter(d => d.level === 'warning');
  const infos = diagnostics.filter(d => d.level === 'info');
  const sorted = [...errors, ...warnings, ...infos];

  return (
    <div className="mt-2">
      <small className="text-white-50 d-block mb-1">Hinweise vom Solver:</small>
      <div className="list-group list-group-flush" style={{ fontSize: '0.8rem' }}>
        {sorted.map((d, i) => (
          <div
            key={i}
            className={`list-group-item py-1 px-2 border-0 ${
              d.level === 'error'
                ? 'bg-danger bg-opacity-10 text-danger'
                : d.level === 'warning'
                  ? 'bg-warning bg-opacity-10 text-dark'
                  : 'bg-info bg-opacity-10 text-dark'
            }`}
            style={{ borderRadius: '4px', marginBottom: '2px' }}
          >
            <DiagnosticIcon level={d.level} />
            <span>{d.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export const RunSolverCard: React.FC<RunSolverCardProps> = ({
  year,
  deliveryWeek,
  deliveryDay,
  csrfToken,
  hasSavedPlan = false,
  onPreviewDetail,
  onApplied,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [running, setRunning] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<SolverDiagnostic[]>([]);

  const [previewResponse, setPreviewResponse] = useState<SolverPreviewResponse | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [detail, setDetail] = useState<SolverPreviewDetailResponse | null>(null);

  const handleRunPreview = async () => {
    setRunning(true);
    setError(null);
    setDiagnostics([]);
    setPreviewResponse(null);
    setDetail(null);
    setSelectedIndex(0);

    try {
      const response = await bakeryApi.bakeryApiBakerySolverPreviewCreate({
        solverPreviewRequestRequest: {
          year,
          deliveryWeek,
          deliveryDay,
          maxSolutions: 10,
        },
      });
      setPreviewResponse(response);
      setDiagnostics((response as any).diagnostics || []);

      // Auto-load detail for first solution
      if (response.totalSolutions > 0) {
        await loadDetail(0);
      }
     } catch (err: any) {
      let message = 'Solver fehlgeschlagen';
      let diags: SolverDiagnostic[] = [];

      // The openapi-generator client wraps the response — try multiple paths
      try {
        const body = err?.response ? await err.response.json() : err?.body;
        if (body) {
          message = body.error || message;
          diags = body.diagnostics || [];
        }
      } catch {
        // If response parsing fails, try direct properties
        message = err?.body?.error || err?.message || message;
        diags = err?.body?.diagnostics || [];
      }

      setError(message);
      setDiagnostics(diags);
    } finally {
      setRunning(false);
    }
  };

  const loadDetail = async (index: number) => {
    setSelectedIndex(index);
    try {
      const detailResponse = await bakeryApi.bakeryApiBakerySolverPreviewDetailRetrieve({
        year,
        deliveryWeek,
        deliveryDay,
        solutionIndex: index,
      });
      setDetail(detailResponse);
      onPreviewDetail?.(detailResponse);
    } catch (err: any) {
      setError(`Fehler beim Laden von Lösung ${index + 1}`);
    }
  };

  const handleApply = async () => {
    setApplying(true);
    setError(null);
    try {
      await bakeryApi.bakeryApiBakerySolverApplyCreate({
        solverApplyRequestRequest: {
          year,
          deliveryWeek,
          deliveryDay,
          solutionIndex: selectedIndex,
        },
      });
      onApplied?.();
    } catch (err: any) {
      const message = err?.body?.error || err?.message || 'Anwenden fehlgeschlagen';
      setError(message);
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="mt-2">
      {/* Run solver button */}
      <button
        className="btn btn-sm btn-light w-100"
        onClick={handleRunPreview}
        disabled={running}
      >
        {running ? (
          <span className="spinner-border spinner-border-sm me-1" />
        ) : (
          <Lightning className="me-1" />
        )}
        {running
          ? 'Berechne Lösungen...'
          : hasSavedPlan
            ? 'Backplan erneut berechnen'
            : 'Backplan berechnen (Vorschau)'}
      </button>

      {/* Solution selector */}
      {previewResponse && previewResponse.totalSolutions > 0 && (
        <div className="mt-2">
          <div className="d-flex align-items-center gap-1 flex-wrap">
            <small className="text-white me-1">
              {previewResponse.totalSolutions} Lösung{previewResponse.totalSolutions > 1 ? 'en' : ''}:
            </small>
            {previewResponse.solutions.map((sol, i) => (
              <button
                key={i}
                className={`btn btn-sm ${i === selectedIndex ? 'btn-light' : 'btn-outline-light'}`}
                style={{ minWidth: '32px', padding: '2px 6px', fontSize: '0.75rem' }}
                onClick={() => loadDetail(i)}
                disabled={running}
                title={`Lösung ${i + 1}: ${sol.totalBaked} Brote, ${sol.sessionsUsed} Ofengänge`}
              >
                {i + 1}
              </button>
            ))}
          </div>

          {/* Apply button */}
          <button
            className="btn btn-sm btn-success w-100 mt-2"
            onClick={handleApply}
            disabled={applying || !detail}
          >
            {applying ? (
              <span className="spinner-border spinner-border-sm me-1" />
            ) : (
              <CheckCircleFill className="me-1" />
            )}
            Lösung {selectedIndex + 1} anwenden
          </button>
        </div>
      )}

      {previewResponse && previewResponse.totalSolutions === 0 && (
        <small className="text-warning d-block mt-1">Keine Lösung gefunden.</small>
      )}

      {/* Error message */}
      {error && (
        <div className="alert alert-danger py-1 px-2 mt-2 mb-0" style={{ fontSize: '0.8rem' }}>
          <XCircleFill className="me-1" />
          {error}
        </div>
      )}

      {/* Diagnostics */}
      <DiagnosticsList diagnostics={diagnostics} />
    </div>
  );
};