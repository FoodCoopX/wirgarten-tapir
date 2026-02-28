import React, { useState } from 'react';
import { Lightning, CheckCircleFill, ExclamationTriangleFill } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { RunSolverResponse } from '../../../api-client/models';

interface RunSolverCardProps {
  year: number;
  deliveryWeek: number;
  deliveryDay: number;
  csrfToken: string;
}

export const RunSolverCard: React.FC<RunSolverCardProps> = ({
  year,
  deliveryWeek,
  deliveryDay,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunSolverResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    

    setRunning(true);
    setResult(null);
    setError(null);

    try {
      const data = await bakeryApi.bakerySolverRunCreate({
        runSolverRequestRequest: {
          year,
          deliveryWeek,
          deliveryDay,
        },
      });
      setResult(data);
    } catch (err: any) {
      // Try to parse the error response JSON
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
    <div className="card" style={{ marginTop: "2mm" }}>
  <div className="d-flex justify-content-center" style={{ marginTop: '2mm' }}>
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
  </div>
      

      <div className="card-body">
        {running && (
          <div className="text-center py-4">
            <div className="spinner-border" style={{ color: '#2E7D32' }} />
            <p className="mt-2 text-muted">
              Optimierung läuft... Dies kann bis zu 60 Sekunden dauern.
            </p>
          </div>
        )}

        {error && (
          <div className="alert alert-danger d-flex align-items-center">
            <p className="small">
            {error}</p>
        </div>
         
        )}

        {result && (
          <>
            <div className="alert alert-success d-flex align-items-center mb-4">
              <CheckCircleFill size={20} className="me-2" />
              <div>
                <strong>Backplan erfolgreich berechnet!</strong>
                
              </div>
            </div>

         

            {/* Quantities */}
            <h6 style={{ color: '#8B4513', fontSize: '0.9rem' }}>Brotmengen</h6>
            <table className="table table-sm table-striped mb-4" style={{ fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th>Brot</th>
                  <th className="text-end">Summe</th>
                  <th className="text-end">für Anteile</th>
                  <th className="text-end">zusätzl.</th>
                </tr>
              </thead>
              <tbody>
                {result.quantities.map((q) => (
                  <tr key={q.breadId}>
                    <td>{q.breadName}</td>
                    <td className="text-end fw-bold">{q.total}</td>
                    <td className="text-end">{q.deliveries}</td>
                    <td className="text-end">
                      {q.remaining > 0 && (
                        <span className="badge bg-warning text-dark">{q.remaining}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Stove Sessions - Vertical Layout */}
            <h6 style={{ color: '#8B4513' }}>Ofenplan</h6>
            <div className="d-flex flex-column gap-2 mb-4">
              {result.stoveSessions.map((session) => (
                <div key={session.session} className="card">
                  <div
                    className="card-header py-1"
                    style={{ backgroundColor: '#D4A574', color: 'white' }}
                  >
                    <small className="fw-bold">Ofengang {session.session}</small>
                  </div>
                  <ul className="list-group list-group-flush">
                    {session.layers.map((layer) => (
                      <li key={layer.layer} className="list-group-item py-1 small">
                        <span className="text-muted">Etage {layer.layer}:</span>{' '}
                        {layer.breadName ? (
                          <span>
                            {layer.breadName}{' '}
                            <span className="badge bg-secondary">×{layer.quantity}</span>
                          </span>
                        ) : (
                          <span className="text-muted fst-italic">leer</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </>
        )}

        
      </div>
    </div>
  );
};