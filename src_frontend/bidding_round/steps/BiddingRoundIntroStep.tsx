import React from "react";
import { Button, Card } from "react-bootstrap";

import { RoundTexts } from "../../api-client";
import NextStepButton from "../../components/mobile_wizard/NextStepButton.tsx";
import { getBiddingRoundLoginUrl } from "../utils/getBiddingRoundLoginUrl.ts";

interface BiddingRoundIntroStepProps {
  texts: RoundTexts;
  isAuthenticated: boolean;
  hasActiveRound: boolean;
  goToNextStep: () => void;
  stepActive: boolean;
}

const BiddingRoundIntroStep: React.FC<BiddingRoundIntroStepProps> = ({
  texts,
  isAuthenticated,
  hasActiveRound,
  goToNextStep,
  stepActive,
}) => {
  if (!hasActiveRound) {
    return (
      <div
        className={"text-center"}
        dangerouslySetInnerHTML={{ __html: texts.endedText }}
      />
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        <Card className={"mb-4"}>
          <Card.Body dangerouslySetInnerHTML={{ __html: texts.introText }} />
        </Card>
        <Card>
          <Card.Body className={"text-center"}>
            {texts.loginTitle && <strong>{texts.loginTitle}</strong>}
            {texts.loginText && (
              <p
                className={"text-muted mt-2"}
                dangerouslySetInnerHTML={{ __html: texts.loginText }}
              />
            )}
            <Button href={getBiddingRoundLoginUrl()} variant={"dark"}>
              Anmelden
            </Button>
          </Card.Body>
        </Card>
      </>
    );
  }

  return (
    <>
      <div
        className={"text-center"}
        dangerouslySetInnerHTML={{ __html: texts.introText }}
      />
      <NextStepButton onClick={goToNextStep} stepActive={stepActive} />
    </>
  );
};

export default BiddingRoundIntroStep;
