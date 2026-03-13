import React from 'react';
import { ChooseBreadsCard, ChoosePreferredBreadsCard } from '../components/cards';

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
      <div className="row">
        <div className="col-md-12 mb-4">
          <ChoosePreferredBreadsCard memberId={memberId} csrfToken={csrfToken} />
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
    </div>
  );
};