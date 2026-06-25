import React, { useState } from "react";
import NextStepButton from "../components/NextStepButton.tsx";
import "../utils/flexColOnSmallScreen.css";

interface Step6BCoopSharesProps {
  goToNextStep: () => void;
}

const Step6BCoopShares: React.FC<Step6BCoopSharesProps> = ({
  goToNextStep,
}) => {
  const [showValidation, setShowValidation] = useState(false);

  return (
    <>
      <div>WIP</div>

      <NextStepButton onClick={() => alert("WIP")} />
    </>
  );
};

export default Step6BCoopShares;
