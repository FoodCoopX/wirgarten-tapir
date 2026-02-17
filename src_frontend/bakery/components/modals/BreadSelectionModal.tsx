import React, { useState, useEffect } from 'react';

interface Bread {
  id: number;
  name: string;
  description?: string;
  available_quantity: number;
}

interface BreadSelection {
  [breadId: number]: number; // breadId -> quantity
}

interface BreadSelectionModalProps {
  memberId: number;
  currentSelection: BreadSelection;
  onSave: (selection: BreadSelection) => void;
  onClose: () => void;
  isOpen: boolean;
}

export const BreadSelectionModal: React.FC<BreadSelectionModalProps> = ({
  memberId,
  currentSelection,
  onSave,
  onClose,
  isOpen,
}) => {
  const [availableBreads, setAvailableBreads] = useState<Bread[]>([]);
  const [selection, setSelection] = useState<BreadSelection>(currentSelection);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      loadAvailableBreads();
    }
  }, [isOpen]);

  const loadAvailableBreads = async () => {
    try {
      // TODO: Call API to get available breads for current delivery
      // const breads = await DeliveryService.getAvailableBreads();
      
      // Mock data for now
      const mockBreads: Bread[] = [
        { id: 1, name: 'Vollkornbrot', description: 'Aus 100% Vollkornmehl', available_quantity: 10 },
        { id: 2, name: 'Sauerteigbrot', description: 'Traditionell mit Sauerteig', available_quantity: 8 },
        { id: 3, name: 'Roggenbrot', description: 'Kräftiger Roggengeschmack', available_quantity: 5 },
        { id: 4, name: 'Dinkelbrötchen', description: '6er Pack', available_quantity: 12 },
      ];
      
      setAvailableBreads(mockBreads);
      setSelection(currentSelection);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load available breads:', error);
      setLoading(false);
    }
  };

  const updateQuantity = (breadId: number, change: number) => {
    setSelection((prev) => {
      const currentQty = prev[breadId] || 0;
      const newQty = Math.max(0, currentQty + change);
      
      if (newQty === 0) {
        const { [breadId]: _, ...rest } = prev;
        return rest;
      }
      
      return { ...prev, [breadId]: newQty };
    });
  };

  const handleSave = () => {
    onSave(selection);
    onClose();
  };

  const getTotalItems = () => {
    return Object.values(selection).reduce((sum, qty) => sum + qty, 0);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="modal-backdrop fade show" 
        onClick={onClose}
        style={{ zIndex: 1040 }}
      />
      
      {/* Modal */}
      <div 
        className="modal fade show d-block" 
        tabIndex={-1}
        style={{ zIndex: 1050 }}
      >
        <div className="modal-dialog modal-lg modal-dialog-scrollable">
          <div className="modal-content">
            {/* Header */}
            <div className="modal-header">
              <h5 className="modal-title">Brotauswahl bearbeiten</h5>
              <button 
                type="button" 
                className="btn-close" 
                onClick={onClose}
                aria-label="Close"
              />
            </div>

            {/* Body */}
            <div className="modal-body">
              {loading ? (
                <div className="text-center py-5">
                  <div className="spinner-border">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                </div>
              ) : (
                <div className="list-group">
                  {availableBreads.map((bread) => {
                    const quantity = selection[bread.id] || 0;
                    const isOutOfStock = bread.available_quantity === 0;
                    
                    return (
                      <div 
                        key={bread.id} 
                        className={`list-group-item ${isOutOfStock ? 'disabled' : ''}`}
                      >
                        <div className="d-flex justify-content-between align-items-center">
                          <div className="flex-grow-1">
                            <h6 className="mb-1">{bread.name}</h6>
                            {bread.description && (
                              <p className="mb-1 text-muted small">{bread.description}</p>
                            )}
                            <small className="text-muted">
                              {isOutOfStock ? (
                                <span className="text-danger">Ausverkauft</span>
                              ) : (
                                `Noch ${bread.available_quantity} verfügbar`
                              )}
                            </small>
                          </div>
                          
                          <div className="d-flex align-items-center gap-2">
                            <button
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => updateQuantity(bread.id, -1)}
                              disabled={quantity === 0 || isOutOfStock}
                            >
                              <span className="material-icons">remove</span>
                            </button>
                            
                            <span className="badge bg-primary rounded-pill" style={{ minWidth: '40px' }}>
                              {quantity}
                            </span>
                            
                            <button
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => updateQuantity(bread.id, 1)}
                              disabled={quantity >= bread.available_quantity || isOutOfStock}
                            >
                              <span className="material-icons">add</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="modal-footer">
              <div className="me-auto">
                <strong>Gesamt: {getTotalItems()} Brote</strong>
              </div>
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={onClose}
              >
                Abbrechen
              </button>
              <button 
                type="button" 
                className="btn btn-primary" 
                onClick={handleSave}
              >
                Speichern
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};