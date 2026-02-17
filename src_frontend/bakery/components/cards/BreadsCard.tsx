import React, { useState, useEffect, useRef } from 'react';
import { BreadModal } from '../modals/BreadModal';
import { BreadContentsModal } from '../modals/BreadContentsModal';
import { LabelsModal } from '../modals/LabelsModal';
import { breadsApi } from '../../types/client';
import type { Bread } from '../../types/api';

export const BreadsCard: React.FC = () => {
  const [breads, setBreads] = useState<Bread[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBreadModal, setShowBreadModal] = useState(false);
  const [showContentsModal, setShowContentsModal] = useState(false);
  const [showLabelsModal, setShowLabelsModal] = useState(false);
  const [editingBread, setEditingBread] = useState<Bread | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const fileInputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({});
    const [showOnlyActive, setShowOnlyActive] = useState(true);


  useEffect(() => {
    loadBreads();
  }, []);

  const loadBreads = async () => {
    setLoading(true);
    try {
      const data = await breadsApi.list();
      setBreads(data);
    } catch (error) {
      console.error('Failed to load breads:', error);
      alert('Fehler beim Laden der Brote');
    } finally {
      setLoading(false);
    }
  };

  const filteredBreads = breads.filter(bread => {
    const matchesSearch = bread.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesActive = showOnlyActive ? bread.is_active : true;
    return matchesSearch && matchesActive;
  });

  const handleCreate = () => {
    setEditingBread(null);
    setShowBreadModal(true);
  };

  const handleEdit = (bread: Bread) => {
    setEditingBread(bread);
    setShowBreadModal(true);
  };

  const handleManageContents = (bread: Bread) => {
    setEditingBread(bread);
    setShowContentsModal(true);
  };

  const handleManageLabels = (bread: Bread) => {
    setEditingBread(bread);
    setShowLabelsModal(true);
  };

  const handleImageClick = (breadId: string) => {
    fileInputRefs.current[breadId]?.click();
  };

  const handleImageUpload = async (breadId: string, file: File) => {
    const formData = new FormData();
    formData.append('picture', file);

    try {
      await breadsApi.updateImage(breadId, formData);
      await loadBreads();
    } catch (error) {
      console.error('Failed to upload image:', error);
      alert('Fehler beim Hochladen des Bildes');
    }
  };

  const handleSaveBread = async (bread: Partial<Bread>) => {
    try {
      if (editingBread) {
        await breadsApi.update(editingBread.id, bread);
      } else {
        await breadsApi.create(bread);
      }

      await loadBreads();
      setShowBreadModal(false);
      setEditingBread(null);
    } catch (error) {
      console.error('Failed to save bread:', error);
      alert('Fehler beim Speichern des Brots');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Brot wirklich löschen?')) return;

    try {
      await breadsApi.delete(id);
      await loadBreads();
    } catch (error) {
      console.error('Failed to delete bread:', error);
      alert('Fehler beim Löschen des Brots');
    }
  };

  return (
    <>
      <div className="card h-100 shadow-sm">
                <div className="card-header border-0" 
             style={{ backgroundColor: '#F5E6D3', color: '#8B4513' }}>
          <div className="d-flex justify-content-between align-items-center gap-2">
            <h5 className="mb-0">Brote</h5>
            <div className="input-group input-group-sm mx-3" style={{ maxWidth: '300px' }}>
              <span className="input-group-text bg-white border-end-0">
                <span className="material-icons" style={{ fontSize: '16px', color: '#8B4513' }}>search</span>
              </span>
              <input
                type="text"
                className="form-control border-start-0"
                placeholder="Brot suchen..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              {searchTerm && (
                <button
                  className="btn btn-sm"
                  type="button"
                  onClick={() => setSearchTerm('')}
                  style={{ color: '#8B4513' }}
                >
                  <span className="material-icons" style={{ fontSize: '16px' }}>close</span>
                </button>
              )}
            </div>
            <div className="form-check form-check-sm mb-0">
              <input
                className="form-check-input"
                type="checkbox"
                id="showOnlyActive"
                checked={showOnlyActive}
                onChange={(e) => setShowOnlyActive(e.target.checked)}
                style={{
                  backgroundColor: showOnlyActive ? '#8B4513' : 'transparent',
                  borderColor: '#8B4513'
                }}
              />
              <label className="form-check-label" htmlFor="showOnlyActive" style={{ fontSize: '0.875rem', whiteSpace: 'nowrap' }}>
                nur aktive
              </label>
            </div>
            <button 
              className="btn btn-sm py-0" 
              style={{ backgroundColor: '#8B4513', color: 'white' }}
              onClick={handleCreate}
            >
              <span className="material-icons" style={{ fontSize: '16px' }}>add</span>
              Neu
            </button>
          </div>
        </div>
        
        <div className="card-body" style={{ backgroundColor: '#FBF8F3' }}>
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border" style={{ color: '#8B4513' }} role="status">
                <span className="visually-hidden">Lädt...</span>
              </div>
            </div>
          ) : filteredBreads.length === 0 ? (
            <div className="text-center py-4 text-muted">
              {searchTerm ? (
                <>
                  <p>Keine Brote gefunden für "{searchTerm}".</p>
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => setSearchTerm('')}>
                    Filter zurücksetzen
                  </button>
                </>
              ) : (
                <>
                  <p>Noch keine Brote vorhanden.</p>
                  <button className="btn btn-sm btn-outline-secondary" onClick={handleCreate}>
                    Erstes Brot hinzufügen
                  </button>
                </>
              )}
            </div>
          ) : (
            <div className="list-group list-group-flush">
              {filteredBreads.map((bread) => (
                <div key={bread.id} className="list-group-item px-0 d-flex justify-content-between align-items-start border-0"
                     style={{ backgroundColor: 'transparent' }}>
                  <div className="d-flex gap-3 flex-grow-1">
                    {/* Bread Image */}
                    <div
                      style={{
                        width: '60px',
                        height: '60px',
                        minWidth: '60px',
                        minHeight: '60px',
                        flexShrink: 0,
                        borderRadius: '8px',
                        cursor: 'pointer',
                        position: 'relative',
                        overflow: 'hidden',
                      }}
                      onClick={() => handleImageClick(bread.id)}
                      title="Bild ändern"
                    >
                      {bread.picture ? (
                        <img 
                          src={bread.picture} 
                          alt={bread.name}
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                            border: '2px solid #F5E6D3'
                          }}
                        />
                      ) : (
                        <div 
                          style={{
                            width: '100%',
                            height: '100%',
                            backgroundColor: '#F5E6D3',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            border: '2px solid #F5E6D3'
                          }}
                        >
                          <span className="material-icons" style={{ fontSize: '30px', color: '#8B4513' }}>bakery_dining</span>
                        </div>
                      )}
                      {/* Hover overlay */}
                      <div
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          right: 0,
                          bottom: 0,
                          backgroundColor: 'rgba(0,0,0,0)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'background-color 0.2s',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.5)'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0)'}
                      >
                        <span 
                          className="material-icons" 
                          style={{ 
                            fontSize: '24px', 
                            color: 'white',
                            opacity: 0,
                            transition: 'opacity 0.2s',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.opacity = '1';
                            if (e.currentTarget.parentElement) {
                              e.currentTarget.parentElement.style.backgroundColor = 'rgba(0,0,0,0.5)';
                            }
                          }}
                        >
                          photo_camera
                        </span>
                      </div>
                    </div>
                    <input
                      type="file"
                      accept="image/*"
                      style={{ display: 'none' }}
                      ref={(el) => (fileInputRefs.current[bread.id] = el)}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleImageUpload(bread.id, file);
                        }
                      }}
                    />
                    
                    <div className="flex-grow-1">
                      <div className="d-flex align-items-center gap-2 mb-1">
                        <h6 className="mb-0">{bread.name}</h6>
                        {!bread.is_active && (
                          <span className="badge bg-secondary">inaktiv</span>
                        )}
                      </div>
                      <small className="text-muted d-block mb-1">{Number(bread.weight).toFixed(0)} g</small>
                      
                      {bread.description && (
                        <p className="mb-0 small text-muted">{bread.description}</p>
                      )}
                    </div>
                  </div>
                  
                 
                  <div className="btn-group btn-group-sm ms-2">
                    <button 
                      className="btn btn-outline-secondary border-0" 
                      title="Bearbeiten"
                      style={{ color: '#757575' }}
                      onClick={() => handleEdit(bread)}
                    >
                      <span className="material-icons" style={{ fontSize: '16px' }}>edit</span>
                    </button>
                    <button 
                      className="btn border-0" 
                      title="Inhaltsstoffe verwalten"
                      style={{ color: '#8B4513' }}
                      onClick={() => handleManageContents(bread)}
                    >
                      <span className="material-icons" style={{ fontSize: '16px' }}>list_alt</span>
                    </button>
                    <button 
                      className="btn border-0" 
                      title="Labels verwalten"
                      style={{ color: '#5D7A4A' }}
                      onClick={() => handleManageLabels(bread)}
                    >
                      <span className="material-icons" style={{ fontSize: '16px' }}>label</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="card-footer border-0 text-muted" style={{ backgroundColor: '#FBF8F3' }}>
          <small>
            {searchTerm 
              ? `${filteredBreads.length} von ${breads.length} Brot${breads.length !== 1 ? 'en' : ''}`
              : `${breads.length} Brot${breads.length !== 1 ? 'e' : ''}`
            }
          </small>
        </div>
      </div>

      {showBreadModal && (
        <BreadModal
          bread={editingBread}
          onSave={handleSaveBread}
          onClose={() => {
            setShowBreadModal(false);
            setEditingBread(null);
          }}
        />
      )}

      {showContentsModal && editingBread && (
        <BreadContentsModal
          bread={editingBread}
          onClose={() => {
            setShowContentsModal(false);
            setEditingBread(null);
          }}
        />
      )}

      {showLabelsModal && editingBread && (
        <LabelsModal
          bread={editingBread}
          onClose={() => {
            setShowLabelsModal(false);
            setEditingBread(null);
          }}
          onUpdate={() => loadBreads()}
        />
      )}
    </>
  );
};