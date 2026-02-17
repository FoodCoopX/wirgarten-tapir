import React, { useState, useEffect } from 'react';
import { labelsApi } from '../../types/client';
import type { Label } from '../../types/api';

export const LabelsCard: React.FC = () => {
  const [labels, setLabels] = useState<Label[]>([]);
  const [loading, setLoading] = useState(true);
  const [newLabelName, setNewLabelName] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');

  useEffect(() => {
    loadLabels();
  }, []);

  const loadLabels = async () => {
    setLoading(true);
    try {
      const data = await labelsApi.list();
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
      await labelsApi.create({ name: newLabelName, is_active: true });
      await loadLabels();
      setNewLabelName('');
    } catch (error) {
      console.error('Failed to create label:', error);
      alert('Fehler beim Erstellen des Labels');
    }
  };

  const handleStartEdit = (label: Label) => {
    setEditingId(label.id);
    setEditingName(label.name);
  };

  const handleSaveEdit = async (id: number) => {
    if (!editingName.trim()) return;

    try {
      await labelsApi.update(id, { name: editingName });
      await loadLabels();
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

  const handleDelete = async (id: number) => {
    if (!confirm('Label wirklich löschen?')) return;

    try {
      await labelsApi.delete(id);
      await loadLabels();
    } catch (error) {
      console.error('Failed to delete label:', error);
      alert('Fehler beim Löschen des Labels');
    }
  };

  const handleToggleActive = async (label: Label) => {
    try {
      await labelsApi.update(label.id, { is_active: !label.is_active });
      await loadLabels();
    } catch (error) {
      console.error('Failed to toggle label:', error);
      alert('Fehler beim Aktualisieren des Labels');
    }
  };

  return (
    <div className="card h-100  shadow-sm">
      <div className="card-header border-0 d-flex justify-content-between align-items-center" 
     style={{ backgroundColor: '#E8F5E9', color: '#2E7D32' }}>
  <h5 className="mb-0">Labels</h5>
</div>
      
      <div className="card-body" style={{ backgroundColor: '#F1F8F4' }}>
        {/* Add new label form */}
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
              className="btn" 
              style={{ backgroundColor: '#2E7D32', color: 'white' }}
              disabled={!newLabelName.trim()}
            >
              <span className="material-icons" style={{ fontSize: '16px' }}>add</span>
            </button>
          </div>
        </form>

        {loading ? (
          <div className="text-center py-4">
            <div className="spinner-border" style={{ color: '#2E7D32' }} role="status">
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
                        if (e.key === 'Enter') handleSaveEdit(label.id);
                        if (e.key === 'Escape') handleCancelEdit();
                      }}
                    />
                    <button
                      className="btn btn-sm btn-success"
                      onClick={() => handleSaveEdit(label.id)}
                      disabled={!editingName.trim()}
                    >
                      <span className="material-icons" style={{ fontSize: '16px' }}>check</span>
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={handleCancelEdit}
                    >
                      <span className="material-icons" style={{ fontSize: '16px' }}>close</span>
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex-grow-1">
                      <span className="badge" style={{ backgroundColor: label.is_active ? '#2E7D32' : '#9E9E9E' }}>
                        {label.name}
                      </span>
                    </div>
                    <div className="btn-group btn-group-sm">
                      <button
                        className="btn border-0"
                        title={label.is_active ? 'Deaktivieren' : 'Aktivieren'}
                        style={{ color: label.is_active ? '#2E7D32' : '#9E9E9E' }}
                        onClick={() => handleToggleActive(label)}
                      >
                        <span className="material-icons" style={{ fontSize: '16px' }}>
                          {label.is_active ? 'toggle_on' : 'toggle_off'}
                        </span>
                      </button>
                      <button
                        className="btn btn-outline-secondary border-0"
                        title="Bearbeiten"
                        style={{ color: '#757575' }}
                        onClick={() => handleStartEdit(label)}
                      >
                        <span className="material-icons" style={{ fontSize: '16px' }}>edit</span>
                      </button>
                      <button
                        className="btn btn-outline-danger border-0"
                        title="Löschen"
                        onClick={() => handleDelete(label.id)}
                      >
                        <span className="material-icons" style={{ fontSize: '16px' }}>delete</span>
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