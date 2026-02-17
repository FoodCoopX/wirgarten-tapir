import React from 'react';
import { BreadsCard } from '../components/cards/BreadsCard';
import { LabelsCard } from '../components/cards/LabelsCard';
import { IngredientsCard } from '../components/cards/IngredientsCard';

export const IngredientsLabelsBreads: React.FC = () => {
  const handleConfigChange = (config: any) => {
    console.log('Config changed:', config);
  };

  return (
    <div className="container-fluid mt-4 px-5">
      <h2 className="mb-4">Zutaten, Labels, Brote</h2>
      
      {/* Product Management Cards */}
      <div className="row">
        <div className="col-lg-3 mb-4">
          <IngredientsCard />
        </div>
        
        <div className="col-lg-2 mb-4">
          <LabelsCard />
        </div>
        
        <div className="col-lg-7 mb-4">
          <BreadsCard />
        </div>
      </div>
    </div>
  );
};