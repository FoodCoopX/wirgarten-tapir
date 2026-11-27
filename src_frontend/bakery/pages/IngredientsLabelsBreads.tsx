import React, { useState } from "react";
import {
  BreadsCard,
  GroupsCard,
  IngredientsCard,
  LabelsCard,
} from "../components/cards";

export const IngredientsLabelsBreads: React.FC = () => {
  // Each card shows what the other edits: the groups list names their breads,
  // the breads list names their group.
  const [breadsVersion, setBreadsVersion] = useState(0);
  const [groupsVersion, setGroupsVersion] = useState(0);

  return (
    <div className="container-fluid mt-4 px-5">
      <h2 className="mb-4">Zutaten, Labels, Brote</h2>

      <div className="row">
        <div className="col-lg-3 mb-4">
          <IngredientsCard />
        </div>

        <div className="col-lg-2 mb-4 d-flex flex-column gap-4">
          <LabelsCard />
          <GroupsCard
            breadsVersion={breadsVersion}
            onGroupsChanged={() => setGroupsVersion((v) => v + 1)}
          />
        </div>

        <div className="col-lg-7 mb-4">
          <BreadsCard
            groupsVersion={groupsVersion}
            onBreadsChanged={() => setBreadsVersion((v) => v + 1)}
          />
        </div>
      </div>
    </div>
  );
};
