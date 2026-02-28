import React, { useState, useEffect, useRef } from 'react';
import { BreadModal } from '../modals/BreadModal';
import { BreadContentsModal } from '../modals/BreadContentsModal';
import { LabelsModal } from '../modals/LabelsModal';
import { Plus, Pencil, ListUl, Tag, Search, XLg, Camera, EggFried } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadList, BreadListRequest } from '../../../api-client/models';

interface BreadsCardProps {
  csrfToken: string;
}

export const BreadsCard: React.FC<BreadsCardProps> = ({ csrfToken }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [breads, setBreads] = useState<BreadList[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBreadModal, setShowBreadModal] = useState(false);
  const [showContentsModal, setShowContentsModal] = useState(false);
  const [showLabelsModal, setShowLabelsModal] = useState(false);
  const [editingBread, setEditingBread] = useState<BreadList | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const fileInputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({});
  const [showOnlyActive, setShowOnlyActive] = useState(true);

useEffect(() => {
    loadBreads();
  }, []);

  const loadBreads = async () => {
    setLoading(true);
    try {
      const data = await bakeryApi.bakeryBreadsListList({});
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
    const matchesActive = showOnlyActive ? bread.isActive !== false : true;
    return matchesSearch && matchesActive;
  });

  const handleCreate = () => {
    setEditingBread(null);
    setShowBreadModal(true);
  };

  const handleEdit = (bread: BreadList) => {
    setEditingBread(bread);
    setShowBreadModal(true);
  };

  const handleManageContents = (bread: BreadList) => {
    setEditingBread(bread);
    setShowContentsModal(true);
  };

  const handleManageLabels = (bread: BreadList) => {
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
      await bakeryApi.bakeryBreadsListPartialUpdateRaw({
        id: breadId,
        patchedBreadListRequest: {} as any,
      }, {
        body: formData,
        headers: {
          'X-CSRFToken': csrfToken,
        },
      } as any);
      await loadBreads();
    } catch (error) {
      console.error('Failed to upload image:', error);
      alert('Fehler beim Hochladen des Bildes');
    }
  };

  const handleSaveBread = async (bread: BreadListRequest) => {
    try {
      if (editingBread) {
        await bakeryApi.bakeryBreadsListPartialUpdate({
          id: editingBread.id!,
          patchedBreadListRequest: bread
        });
      } else {
        await bakeryApi.bakeryBreadsListCreate({
          breadListRequest: bread
        });
      }

      await loadBreads();
      setShowBreadModal(false);
      setEditingBread(null);
    } catch (error) {
      console.error('Failed to save bread:', error);
      alert('Fehler beim Speichern des Brots');
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
                <Search size={14} style={{ color: '#8B4513' }} />
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
                  <XLg size={14} />
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
              className="btn btn-sm py-0 d-inline-flex align-items-center gap-1" 
              style={{ backgroundColor: '#8B4513', color: 'white' }}
              onClick={handleCreate}
            >
              <Plus size={16} /> neu
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
                      className="bread-image-container"
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
                      onClick={() => handleImageClick(bread.id!)}
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
                            border: '2px solid #F5E6D3',
                            borderRadius: '8px',
                          }}
                        >
                          <EggFried size={28} style={{ color: '#8B4513' }} />
                        </div>
                      )}
                      {/* Hover overlay */}
                      <div
                        className="bread-image-overlay"
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
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.5)';
                          const icon = e.currentTarget.querySelector('.camera-icon') as HTMLElement;
                          if (icon) icon.style.opacity = '1';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0)';
                          const icon = e.currentTarget.querySelector('.camera-icon') as HTMLElement;
                          if (icon) icon.style.opacity = '0';
                        }}
                      >
                        <Camera 
                          size={22} 
                          className="camera-icon"
                          style={{ 
                            color: 'white',
                            opacity: 0,
                            transition: 'opacity 0.2s',
                          }}
                        />
                      </div>
                    </div>
                    <input
                      type="file"
                      accept="image/*"
                      style={{ display: 'none' }}
                      ref={(el) => (fileInputRefs.current[bread.id!] = el)}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleImageUpload(bread.id!, file);
                        }
                      }}
                    />
                    
                    <div className="flex-grow-1">
                      <div className="d-flex align-items-center gap-2 mb-1">
                        <h6 className="mb-0">{bread.name}</h6>
                        {!bread.isActive && (
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
                      <Pencil size={16} />
                    </button>
                    <button 
                      className="btn border-0" 
                      title="Inhaltsstoffe verwalten"
                      style={{ color: '#8B4513' }}
                      onClick={() => handleManageContents(bread)}
                    >
                      <ListUl size={16} />
                    </button>
                    <button 
                      className="btn border-0" 
                      title="Labels verwalten"
                      style={{ color: '#5D7A4A' }}
                      onClick={() => handleManageLabels(bread)}
                    >
                      <Tag size={16} />
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
          csrfToken={csrfToken}
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
          csrfToken={csrfToken}
          onClose={() => {
            setShowContentsModal(false);
            setEditingBread(null);
          }}
        />
      )}

      {showLabelsModal && editingBread && (
        <LabelsModal
          bread={editingBread}
          csrfToken={csrfToken}
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