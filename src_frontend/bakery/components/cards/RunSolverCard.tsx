import React, { useState } from 'react';
import { Lightning, CheckCircleFill } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type {
  SolverPreviewResponse,
  SolverPreviewDetailResponse,
} from '../../../api-client/models';

interface RunSolverCardProps {
  year: number;
  deliveryWeek: number;
  deliveryDay: number;
  csrfToken: string;
  hasSavedPlan?: boolean;
  onPreviewDetail?: (detail: SolverPreviewDetailResponse) => void;
  onApplied?: () => void;
}

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

  const [previewResponse, setPreviewResponse] = useState<SolverPreviewResponse | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [detail, setDetail] = useState<SolverPreviewDetailResponse | null>(null);

  const handleRunPreview = async () => {
    setRunning(true);
    setError(null);
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

      // Auto-load detail for first solution
      if (response.totalSolutions > 0) {
        await loadDetail(0);
      }
    } catch (err: any) {
      const message = err?.body?.error || err?.message || 'Solver fehlgeschlagen';
      setError(message);
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

      {error && <small className="text-danger d-block mt-1">{error}</small>}
    </div>
  );
};