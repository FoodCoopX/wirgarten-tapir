import React, { useState, useEffect } from 'react';
import { BakeryApi } from '../../../api-client';
import { Plus, Pencil, Trash, Check, X, ToggleOn, ToggleOff } from 'react-bootstrap-icons';
import { useApi } from '../../../hooks/useApi';
import type { BreadLabel, BreadLabelRequest } from '../../../api-client/models';

interface LabelsCardProps {
  csrfToken: string;
}

export const LabelsCard: React.FC<LabelsCardProps> = ({ csrfToken }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [labels, setLabels] = useState<BreadLabel[]>([]);
  const [loading, setLoading] = useState(true);
  const [newLabelName, setNewLabelName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  useEffect(() => {
    loadLabels();
  }, []);

  const loadLabels = async () => {
    setLoading(true);
    try {
      const data = await bakeryApi.bakeryLabelsList();
      setLabels(data);
    } catch (error) {
      console.error('Failed to load labels:', error);
      alert('Fehler beim Laden der Labels');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLabelName.trim()) return;

    try {
      const payload: BreadLabelRequest = { 
        name: newLabelName, 
        isActive: true 
      };
      await bakeryApi.bakeryLabelsCreate({ breadLabelRequest: payload });
      setNewLabelName('');
      await loadLabels();
    } catch (error) {
      console.error('Failed to create label:', error);
      alert('Fehler beim Erstellen des Labels');
    }
  };

  const handleStartEdit = (label: BreadLabel) => {
    setEditingId(label.id!);
    setEditingName(label.name);
  };

  const handleSaveEdit = async (id: string) => {
    if (!editingName.trim()) return;

    try {
      await bakeryApi.bakeryLabelsPartialUpdate({
        id,
        patchedBreadLabelRequest: { name: editingName }
      });
      // Optimistic update
      setLabels(prev => prev.map(l => l.id === id ? { ...l, name: editingName } : l));
      setEditingId(null);
      setEditingName('');
    } catch (error) {
      console.error('Failed to update label:', error);
      alert('Fehler beim Aktualisieren des Labels');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingName('');
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Label wirklich löschen?')) return;

    try {
      await bakeryApi.bakeryLabelsDestroy({ id });
      // Optimistic update
      setLabels(prev => prev.filter(l => l.id !== id));
    } catch (error) {
      console.error('Failed to delete label:', error);
      alert('Fehler beim Löschen des Labels');
    }
  };

  const handleToggleActive = async (label: BreadLabel) => {
    // Optimistic update first — no flicker
    setLabels(prev => prev.map(l => 
      l.id === label.id ? { ...l, isActive: !l.isActive } : l
    ));

    try {
      await bakeryApi.bakeryLabelsPartialUpdate({
        id: label.id!,
        patchedBreadLabelRequest: { isActive: !label.isActive }
      });
    } catch (error) {
      // Revert on failure
      setLabels(prev => prev.map(l => 
        l.id === label.id ? { ...l, isActive: label.isActive } : l
      ));
      console.error('Failed to toggle label:', error);
      alert('Fehler beim Aktualisieren des Labels');
    }
  };

  return (
    <div className="card h-100 shadow-sm">
      <div className="card-header border-0 d-flex justify-content-between align-items-center" 
           style={{ backgroundColor: '#E8F5E9', color: '#2E7D32' }}>
        <h5 className="mb-0">Labels</h5>
      </div>
      
      <div className="card-body" style={{ backgroundColor: '#F1F8F4' }}>
        <form onSubmit={handleCreate} className="mb-4">
          <div className="input-group">
            <input
              type="text"
              className="form-control"
              placeholder="Neues Label..."
              value={newLabelName}
              onChange={(e) => setNewLabelName(e.target.value)}
            />
            <button 
              type="submit" 
              className="btn white-on-green" 
              disabled={!newLabelName.trim()}
            >
              <Plus size={16} />
            </button>
          </div>
        </form>

        {loading ? (
          <div className="text-center py-4">
            <div className="spinner-border white-on-green" role="status">
              <span className="visually-hidden">Lädt...</span>
            </div>
          </div>
        ) : labels.length === 0 ? (
          <div className="text-center py-4 text-muted">
            <p>Noch keine Labels vorhanden.</p>
          </div>
        ) : (
          <div className="list-group list-group-flush">
            {labels.map((label) => (
              <div 
                key={label.id} 
                className="list-group-item px-0 d-flex justify-content-between align-items-center border-0"
                style={{ backgroundColor: 'transparent' }}
              >
                {editingId === label.id ? (
                  <div className="flex-grow-1 d-flex align-items-center gap-2">
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveEdit(label.id!);
                        if (e.key === 'Escape') handleCancelEdit();
                      }}
                    />
                    <button
                      className="btn btn-sm btn-success"
                      onClick={() => handleSaveEdit(label.id!)}
                      disabled={!editingName.trim()}
                    >
                      <Check size={16} />
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={handleCancelEdit}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex-grow-1">
                      <span className="badge" style={{ backgroundColor: label.isActive ? '#2E7D32' : '#9E9E9E' }}>
                        {label.name}
                      </span>
                    </div>
                    <div className="btn-group btn-group-sm">
                      <button
                        className="btn border-0"
                        title={label.isActive ? 'Deaktivieren' : 'Aktivieren'}
                        style={{ color: label.isActive ? '#2E7D32' : '#9E9E9E' }}
                        onClick={() => handleToggleActive(label)}
                      >
                        {label.isActive ? <ToggleOn size={16} /> : <ToggleOff size={16} />}
                      </button>
                      <button
                        className="btn btn-outline-secondary border-0"
                        title="Bearbeiten"
                        style={{ color: '#757575' }}
                        onClick={() => handleStartEdit(label)}
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        className="btn btn-outline-danger border-0"
                        title="Löschen"
                        onClick={() => handleDelete(label.id!)}
                      >
                        <Trash size={16} />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="card-footer border-0 text-muted" style={{ backgroundColor: '#F1F8F4' }}>
        <small>{labels.length} Label{labels.length !== 1 ? 's' : ''}</small>
      </div>
    </div>
  );
};