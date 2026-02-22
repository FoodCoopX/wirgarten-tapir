  import React from 'react';
  import { PreferredLabelsCard } from '../components/cards/PreferredLabelsCard';
  import { ChooseBreadsCard } from '../components/cards/ChooseBreadsCard';
import { YearWeekSelectorCard } from '../components/cards/YearWeekSelectorCard';

  interface ChooseBreadsProps {
    memberId: string;
    csrfToken: string;
    chooseStationPerBread: boolean;
  }

  export const ChooseBreads: React.FC<ChooseBreadsProps> = ({ memberId, csrfToken, chooseStationPerBread }) => {
    return (
      <div className="container-fluid mt-4 px-5">
        
        
        <div className="row">
          <div className="col-md-6 mb-4">
            <PreferredLabelsCard csrfToken={csrfToken} memberId={memberId} />
          </div>
        </div>
      
         
      <div className="row">
          <div className="col-md-12 mb-4">
            <ChooseBreadsCard chooseStationPerBread={chooseStationPerBread} csrfToken={csrfToken} memberId={memberId} />
          </div>
        </div>
        
      </div>
    );
  };