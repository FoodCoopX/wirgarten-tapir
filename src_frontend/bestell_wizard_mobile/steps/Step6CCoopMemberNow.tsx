import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import "../utils/flexColOnSmallScreen.css";
import { Step } from "../types/Step.ts";

interface Step6CCoopMemberNowProps {
  setCurrentStep: (step: Step) => void;
  setBecomeMemberNow: (becomeMemberNow: boolean) => void;
}

const Step6CCoopMemberNow: React.FC<Step6CCoopMemberNowProps> = ({
  setCurrentStep,
  setBecomeMemberNow,
}) => {
  return (
    <>
      <p>
        Die wirst auf die Warteliste für deine Bestellung eingetragen. Du kannst
        dich aber entscheiden sofort Mitglied der Genossenschaft zu werden.
      </p>
      <h5 className={"text-center mb-0"}>Sofort Mitglied werden</h5>
      <p className={"mb-0"}>
        Deine Bestellung geht auf der Warteliste bis ein Platz für dich frei
        wird. Du kaufst aber gleich Genossenschaftsanteile. Du wirst sofort
        Mitglied der Genossenschaft.
      </p>
      <TapirButton
        text={"Sofort Mitglied werden"}
        variant={BUTTON_VARIANT}
        onClick={() => {
          setBecomeMemberNow(true);
          setTimeout(() => setCurrentStep("6b_coop_shares"), 100);
        }}
        icon={"id_card"}
        size={"sm"}
      />
      <h5 className={"text-center mb-0 mt-2"}>
        Erst Mitglied werden wenn die Bestellung bestätigt wird
      </h5>
      <p className={"mb-0"}>
        Deine Bestellung geht auf der Warteliste bis ein Platz für dich frei
        wird. Erst wenn ein Platz für dich frei wird kaufst du
        Genossenschaftsanteile. Erst dann wirst du Mitglied der Genossenschaft.
      </p>
      <TapirButton
        text={"Später Mitglied werden"}
        variant={BUTTON_VARIANT}
        onClick={() => {
          setBecomeMemberNow(false);
          setTimeout(() => setCurrentStep("8_personal_data"), 100);
        }}
        icon={"pending_actions"}
        size={"sm"}
      />
    </>
  );
};

export default Step6CCoopMemberNow;
