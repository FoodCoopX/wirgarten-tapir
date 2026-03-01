import React, { useState } from 'react';
import { Lightning, CheckCircleFill } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';

interface RunSolverCardProps {
  year: number;
  deliveryWeek: number;
  deliveryDay: number;
  csrfToken: string;
  onSuccess?: () => void;
}

export const RunSolverCard: React.FC<RunSolverCardProps> = ({
  year,
  deliveryWeek,
  deliveryDay,
  csrfToken,
  onSuccess,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [running, setRunning] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setRunning(true);
    setSuccess(false);
    setError(null);

    try {
      await bakeryApi.bakerySolverRunCreate({
        runSolverRequestRequest: {
          year,
          deliveryWeek,
          deliveryDay,
        },
      });
      setSuccess(true);
      onSuccess?.();
    } catch (err: any) {
      let errorMessage = 'Unbekannter Fehler';
      if (err.response) {
        try {
          const errorData = await err.response.json();
          errorMessage = errorData.error || errorData.detail || JSON.stringify(errorData);
        } catch {
          errorMessage = err.response.statusText || `HTTP ${err.response.status}`;
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="d-flex flex-column align-items-center gap-2" style={{ marginTop: '2mm' }}>
      <button
        className="btn btn-sm"
        style={{ backgroundColor: '#8B4513', color: 'white' }}
        onClick={handleRun}
        disabled={running}
      >
        {running ? (
          <>
            <span className="spinner-border spinner-border-sm me-2" />
            Berechne...
          </>
        ) : (
          <>
            <Lightning size={16} className="me-1" />
            Backplan berechnen
          </>
        )}
      </button>

      {success && (
        <div className="alert alert-success d-flex align-items-center py-1 px-2 mb-0" style={{ fontSize: '0.8rem' }}>
          <CheckCircleFill size={14} className="me-1" />
          <span>Backplan berechnet!</span>
        </div>
      )}

      {error && (
        <div className="alert alert-danger py-1 px-2 mb-0" style={{ fontSize: '0.8rem' }}>
          {error}
        </div>
      )}
    </div>
  );
};