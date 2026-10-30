import React from "react";
import { Button } from "react-bootstrap";
import NextStepButton from "../../bestell_wizard_mobile/components/NextStepButton.tsx";
import {
  BiddingRoundPublicEvaluation,
  BiddingRoundRound,
  BiddingRoundTexts,
} from "../types/BiddingRoundTypes.ts";
import { getBiddingRoundLoginUrl } from "../utils/getBiddingRoundLoginUrl.ts";
import BiddingRoundEvaluation from "./BiddingRoundEvaluation.tsx";

interface BiddingRoundIntroStepProps {
  texts: BiddingRoundTexts;
  round: BiddingRoundRound;
  evaluation: BiddingRoundPublicEvaluation | null;
  isAuthenticated: boolean;
  goToNextStep: () => void;
  stepActive: boolean;
}

const BiddingRoundIntroStep: React.FC<BiddingRoundIntroStepProps> = ({
  texts,
  round,
  evaluation,
  isAuthenticated,
  goToNextStep,
  stepActive,
}) => {
  const isTrafficLight = round.biddingProcedure === "traffic_light";
  const bidLevels = Math.min(Math.max(round.bidLevels ?? 1, 1), 3);
  // Explanation of the bidding principle, independent of the evaluation.
  const biddingExplanation = isTrafficLight
    ? texts.bid.trafficLightExplanation
    : bidLevels > 1
      ? texts.bid.simpleLevelsExplanation
      : texts.bid.simpleExplanation;

  return (
    <>
      {texts.introText && (
        <p
          className={"text-center"}
          dangerouslySetInnerHTML={{ __html: texts.introText }}
        />
      )}
      {biddingExplanation && (
        <p
          className={"text-muted text-center"}
          dangerouslySetInnerHTML={{ __html: biddingExplanation }}
        />
      )}
      {evaluation && (
        <BiddingRoundEvaluation texts={texts} evaluation={evaluation} />
      )}
      {isAuthenticated ? (
        <NextStepButton onClick={goToNextStep} stepActive={stepActive} />
      ) : (
        <div className={"d-flex flex-column gap-2 align-items-center"}>
          {texts.loginTitle && <strong>{texts.loginTitle}</strong>}
          {texts.loginText && (
            <p
              className={"text-center text-muted mb-0"}
              dangerouslySetInnerHTML={{ __html: texts.loginText }}
            />
          )}
          <Button href={getBiddingRoundLoginUrl()} variant={"dark"}>
            {"Anmelden"}
          </Button>
        </div>
      )}
    </>
  );
};

export default BiddingRoundIntroStep;
