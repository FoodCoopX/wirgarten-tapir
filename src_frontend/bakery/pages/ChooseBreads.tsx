import React from 'react';
import { Basket, Star, ArrowDown } from 'react-bootstrap-icons';
import { ChooseBreadsCard, ChoosePreferredBreadsCard } from '../components/cards';
import '../styles/bakery_styles.css';

interface ChooseBreadsProps {
  memberId: string;
  csrfToken: string;
  chooseStationPerBread: boolean;
  membersCanChooseBreadSorts: boolean;
}

export const ChooseBreads: React.FC<ChooseBreadsProps> = ({ 
  memberId, 
  csrfToken, 
  chooseStationPerBread, 
  membersCanChooseBreadSorts 
}) => {
  return (
    <div className="container-fluid mt-4 px-5">
      {/* Page Introduction */}
      <div className="row mb-4">
        <div className="col-12">
          <div className="text-center mb-4">
            <h2 className="text-bakery-primary-darker">Deine Brotauswahl</h2>
            <p className="text-muted">
              {membersCanChooseBreadSorts 
                ? 'Hier kannst du dein Brot auswählen – entweder direkt für eine bestimmte Woche oder als Lieblingsbrot für die automatische Zuteilung.'
                : 'Hier kannst du deine Lieblingsbrote festlegen, die bei der automatischen Zuteilung bevorzugt werden.'}
            </p>
          </div>
        </div>
      </div>

      {/* Section 1: Direct Bread Selection - only when members CAN choose bread sorts */}
      {membersCanChooseBreadSorts && (
        <div className="row">
          <div className="col-12 mb-3">
            <div className="d-flex align-items-center gap-2 mb-2">
              <div className="section-step-circle section-step-bakery">
                1
              </div>
              <h4 className="mb-0 text-bakery-primary-darker">
                Brot direkt auswählen
              </h4>
            </div>
            <p className="text-muted ms-5 mb-0">
              <strong>Optional:</strong> Wähle ein bestimmtes Brot für eine bestimmte Woche aus. 
              Dies überschreibt die automatische Zuteilung für diese Lieferung.
            </p>
          </div>
          <div className="col-md-12 mb-4">
            <ChooseBreadsCard 
              chooseStationPerBread={chooseStationPerBread} 
              membersCanChooseBreadSorts={membersCanChooseBreadSorts} 
              csrfToken={csrfToken} 
              memberId={memberId} 
            />
          </div>
        </div>
      )}

      {/* Visual Separator with Arrow - only when both sections are shown */}
      {membersCanChooseBreadSorts && (
        <div className="row mb-4">
          <div className="col-12 text-center">
            <div className="d-flex align-items-center justify-content-center gap-3">
              <hr className="hr-bakery" style={{ flex: 1 }} />
              <div className="separator-circle">
                <ArrowDown size={24} className="icon-bakery-primary-darker" />
              </div>
              <hr className="hr-bakery" style={{ flex: 1 }} />
            </div>
            <p className="text-muted small mt-2 mb-0">
              Keine bestimmte Auswahl getroffen? Kein Problem! Deine Lieblingsbrote werden bevorzugt.
            </p>
          </div>
        </div>
      )}

      {/* Section 2: Preferred Breads - always shown */}
      <div className="row">
        <div className="col-12 mb-3">
          <div className="d-flex align-items-center gap-2 mb-2">
            <div className="section-step-circle section-step-gold">
              {membersCanChooseBreadSorts ? '2' : ''}
            </div>
            <h4 className="mb-0 text-bakery-primary-darker">
              
              Lieblingsbrote festlegen
            </h4>
          </div>
          <p className="text-muted ms-5 mb-0">
            {membersCanChooseBreadSorts ? (
              <>
                <strong>Empfohlen:</strong> Wähle deine Lieblingsbrote aus. 
                Wenn du oben kein Brot direkt gewählt hast, versuchen wir deinen Abholort mit deinen Favoriten zu bestücken.
              </>
            ) : (
              <>
                Wähle deine Lieblingsbrote aus. 
                Wir versuchen deinen Abholort mit deinen Favoriten zu bestücken.
              </>
            )}
          </p>
        </div>
        <div className="col-md-12 mb-4">
          <ChoosePreferredBreadsCard memberId={memberId} csrfToken={csrfToken} />
        </div>
      </div>
    </div>
  );
};