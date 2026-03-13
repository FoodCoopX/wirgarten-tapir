import React from 'react';
import { BreadsCard, LabelsCard, IngredientsCard } from '../components/cards';

interface IngredientsLabelsBreadsProps {
  csrfToken: string;
}

export const IngredientsLabelsBreads: React.FC<IngredientsLabelsBreadsProps> = ({ csrfToken }) => {
  return (
    <div className="container-fluid mt-4 px-5">
      <h2 className="mb-4">Zutaten, Labels, Brote</h2>
      
      <div className="row">
        <div className="col-lg-3 mb-4">
          <IngredientsCard csrfToken={csrfToken} />
        </div>
        
        <div className="col-lg-2 mb-4">
          <LabelsCard csrfToken={csrfToken} />
        </div>
        
        <div className="col-lg-7 mb-4">
          <BreadsCard csrfToken={csrfToken} />
        </div>
      </div>
    </div>
  );
};