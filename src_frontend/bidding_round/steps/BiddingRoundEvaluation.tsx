import React, { useState } from "react";
import { Card, Form } from "react-bootstrap";

import DeckungAuslastungBars from "../../components/DeckungAuslastungBars.tsx";
import { interpolate } from "../../utils/interpolate.ts";
import {
  formatEuro,
  interpolateLevel,
  levelFromPosition,
} from "../../utils/resultsFormat.ts";
import {
  BiddingRoundPublicEvaluation,
  BiddingRoundTexts,
} from "../types/BiddingRoundTypes.ts";
import {
  TRAFFIC_LIGHT_LEVELS,
  getTrafficLightLabel,
} from "../utils/trafficLightLevels.ts";

interface BiddingRoundEvaluationProps {
  texts: BiddingRoundTexts;
  evaluation: BiddingRoundPublicEvaluation;
}

// Stripped-down public variant of the admin evaluation: a slider (bid levels for
// a simple round with several bids, green (wish) -> red (pain threshold) for the
// traffic light), the average
// contributions and the utilization/coverage bars. Same look and feel as the
// admin results page.
const BiddingRoundEvaluation: React.FC<BiddingRoundEvaluationProps> = ({
  texts,
  evaluation,
}) => {
  const isTrafficLight = evaluation.biddingProcedure === "traffic_light";
  const bidLevels = isTrafficLight
    ? 3
    : Math.min(Math.max(evaluation.bidLevels ?? 1, 1), 3);
  const [position, setPosition] = useState(() =>
    Number(evaluation.trafficLightPosition ?? 50),
  );

  const levels = evaluation.levels;
  const currentCoverage = interpolateLevel(
    Number(levels.green.currentCoveragePercent),
    Number(levels.yellow.currentCoveragePercent),
    Number(levels.red.currentCoveragePercent),
    position,
  );
  const currentTotal = interpolateLevel(
    Number(levels.green.currentTotalPerYear),
    Number(levels.yellow.currentTotalPerYear),
    Number(levels.red.currentTotalPerYear),
    position,
  );
  const bidderAveragePerMonth = interpolateLevel(
    Number(levels.green.bidderAveragePerMonth),
    Number(levels.yellow.bidderAveragePerMonth),
    Number(levels.red.bidderAveragePerMonth),
    position,
  );

  const levelLabels = [
    texts.bid.level1Label,
    texts.bid.level2Label,
    texts.bid.level3Label,
  ];

  const sliderHint = isTrafficLight
    ? texts.statsTrafficLightSliderHint
    : bidLevels > 1
      ? texts.statsSimpleLevelsSliderHint
      : "";

  return (
    <Card className="mt-2" style={{ width: "100%", maxWidth: "720px" }}>
      <Card.Body>
        <Card.Title className="text-center">{texts.statsTitle}</Card.Title>
        {texts.statsText && (
          <p
            className="text-center"
            dangerouslySetInnerHTML={{ __html: texts.statsText }}
          />
        )}
        {texts.statsExplanation && (
          <p
            className="text-center"
            dangerouslySetInnerHTML={{ __html: texts.statsExplanation }}
          />
        )}
        {sliderHint && (
          <p
            className="text-muted small"
            dangerouslySetInnerHTML={{ __html: sliderHint }}
          />
        )}

        {isTrafficLight && (
          <>
            <div className="position-relative">
              <div
                style={{
                  height: "0.5rem",
                  borderRadius: "0.25rem",
                  background:
                    "linear-gradient(90deg, #198754 0%, #ffc107 50%, #dc3545 100%)",
                  opacity: 0.5,
                }}
              />
              <Form.Range
                min={0}
                max={100}
                step={1}
                value={position}
                onChange={(event) => setPosition(Number(event.target.value))}
                className="w-100"
                style={{ marginTop: "-0.95rem" }}
                aria-label={"Solidaritätsniveau"}
              />
            </div>
            <div className="d-flex justify-content-between small">
              {TRAFFIC_LIGHT_LEVELS.map((level) => (
                <span className={level.textClass} key={level.key}>
                  <span
                    className={
                      "d-inline-block rounded-circle me-1 " + level.dotClass
                    }
                    style={{ width: "0.6rem", height: "0.6rem" }}
                  />
                  {getTrafficLightLabel(level, texts.bid)}
                </span>
              ))}
            </div>
          </>
        )}

        {!isTrafficLight && bidLevels > 1 && (
          <>
            <Form.Range
              min={1}
              max={bidLevels}
              step={1}
              value={levelFromPosition(position, bidLevels)}
              onChange={(event) =>
                setPosition((Number(event.target.value) - 1) * 50)
              }
              className="w-100"
              aria-label={"Gebotsstufe"}
            />
            <div className="d-flex justify-content-between small text-muted">
              {Array.from({ length: bidLevels }, (_, index) => index + 1).map(
                (level) => (
                  <span key={level}>{levelLabels[level - 1]}</span>
                ),
              )}
            </div>
          </>
        )}

        <div className="row mt-3 align-items-center">
          <div className="col-md-6">
            <div className="display-6">{formatEuro(bidderAveragePerMonth)}</div>
            <div>
              <span className="text-muted small">
                {"/ Anteil / Monat für"}{" "}
              </span>
              <span className="fw-bold fs-5">{"Bietende Ø"}</span>
            </div>
            <div className="text-muted small">
              {interpolate("= {amount} / Anteil / Jahr Ø", {
                amount: formatEuro(bidderAveragePerMonth * 12),
              })}
            </div>
          </div>
          <div className="col-md-6">
            <DeckungAuslastungBars
              utilization={Number(evaluation.utilizationPercent)}
              currentShares={Number(evaluation.currentShares)}
              capacityShares={Number(evaluation.capacityShares)}
              currentCoverage={currentCoverage}
              currentTotal={currentTotal}
              target={Number(evaluation.targetPerYear)}
            />
          </div>
        </div>
      </Card.Body>
    </Card>
  );
};

export default BiddingRoundEvaluation;
