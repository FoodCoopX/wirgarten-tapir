  import React from 'react';
  import { PreferredLabelsCard } from '../components/cards/PreferredLabelsCard';
  import { ChooseBreadsCard } from '../components/cards/ChooseBreadsCard';

  interface ChooseBreadsProps {
    memberId: string;
  }

  export const ChooseBreads: React.FC<ChooseBreadsProps> = ({ memberId }) => {
    return (
      <div className="container-fluid mt-4 px-5">
        
        
        <div className="row">
          <div className="col-md-6 mb-4">
            <PreferredLabelsCard memberId={memberId} />
          </div>
        </div>
       
      <div className="row">
          <div className="col-md-12 mb-4">
            <ChooseBreadsCard memberId={memberId} />
          </div>
        </div>
        
      </div>
    );
  };