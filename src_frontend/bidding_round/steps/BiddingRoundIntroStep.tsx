import React from "react";
import { Badge, Button, Card, ProgressBar } from "react-bootstrap";

import { PublicEvaluationResponse, RoundTexts } from "../../api-client";
import NextStepButton from "../../components/mobile_wizard/NextStepButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { getBiddingRoundLoginUrl } from "../utils/getBiddingRoundLoginUrl.ts";

const COVERAGE_STATUS_VARIANT: Record<string, string> = {
  green: "success",
  yellow: "warning",
  red: "danger",
};

const COVERAGE_STATUS_LABEL: Record<string, string> = {
  green: "Grün",
  yellow: "Gelb",
  red: "Rot",
};

interface BiddingRoundIntroStepProps {
  texts: RoundTexts;
  isAuthenticated: boolean;
  hasActiveRound: boolean;
  liveEvaluation: PublicEvaluationResponse | null;
  goToNextStep: () => void;
  stepActive: boolean;
}

const BiddingRoundIntroStep: React.FC<BiddingRoundIntroStepProps> = ({
  texts,
  isAuthenticated,
  hasActiveRound,
  liveEvaluation,
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

  const coverageStatusVariant = liveEvaluation
    ? (COVERAGE_STATUS_VARIANT[liveEvaluation.coverageStatus] ?? "secondary")
    : "secondary";

  return (
    <>
      <div
        className={"text-center"}
        dangerouslySetInnerHTML={{ __html: texts.introText }}
      />
      {liveEvaluation && (
        <Card className={"mb-4"}>
          <Card.Header>
            <strong>Zwischenstand</strong>
            <Badge bg={coverageStatusVariant} className={"ms-2"}>
              {COVERAGE_STATUS_LABEL[liveEvaluation.coverageStatus] ??
                liveEvaluation.coverageStatus}
            </Badge>
          </Card.Header>
          <Card.Body>
            <div className={"d-flex justify-content-between mb-1"}>
              <span>Deckung</span>
              <strong>{liveEvaluation.coveragePercent.toFixed(1)} %</strong>
            </div>
            <ProgressBar
              now={Math.min(liveEvaluation.coveragePercent, 100)}
              variant={coverageStatusVariant}
              className={"mb-3"}
            />
            <div className={"d-flex justify-content-between mb-1"}>
              <span>Auslastung</span>
              <strong>{liveEvaluation.utilizationPercent.toFixed(1)} %</strong>
            </div>
            <ProgressBar
              now={Math.min(liveEvaluation.utilizationPercent, 100)}
              variant={"info"}
              className={"mb-3"}
            />
            <div className={"text-muted small"}>
              Bietende Ø{" "}
              {formatCurrency(Number(liveEvaluation.bidderAveragePerMonth))} /
              Monat
            </div>
          </Card.Body>
        </Card>
      )}
      <NextStepButton onClick={goToNextStep} stepActive={stepActive} />
    </>
  );
};

export default BiddingRoundIntroStep;
