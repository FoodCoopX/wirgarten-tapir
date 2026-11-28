import React, { Fragment } from "react";
import { Badge } from "react-bootstrap";
import { SegmentData, SegmentOption, TypeEnum } from "tapir-api-client";
import "./chainedBadges.css";

interface SegmentsDisplayProps {
  segmentData: SegmentData;
  interactions?: {
    onSegmentToAddClicked: (segment: string) => void;
    onSegmentToRemoveClicked: (segment: string) => void;
    onStaticSegmentToAddClicked: (segment: string) => void;
    onStaticSegmentToRemoveClicked: (segment: string) => void;
    onMailCategoryIdClicked: (segment: string) => void;
  };
  availableSegments: SegmentOption[];
}

const SegmentsDisplay: React.FC<SegmentsDisplayProps> = ({
  segmentData,
  interactions,
  availableSegments,
}) => {
  if (
    segmentData.dynamicSegmentNamesAdditive.length +
      segmentData.staticSegmentIdsAdditive.length +
      segmentData.mailCategoryIdsAdditive.length ===
    0
  ) {
    return null;
  }

  function buildLabel(type: TypeEnum, id: string) {
    const option = availableSegments.find(
      (segment) => segment.type === type && segment.id === id,
    );
    return <span title={option?.description}>{option?.label ?? id}</span>;
  }

  const segmentStyle: React.CSSProperties = interactions
    ? { cursor: "pointer" }
    : {};

  return (
    <div style={{ marginBottom: "0.5em" }}>
      <h6 className="chained-badges">
        {segmentData.dynamicSegmentNamesAdditive.map((segmentId, idx) => (
          <Fragment key={segmentId}>
            {idx > 0 && <OperatorBadge text="+" />}
            <Badge
              style={segmentStyle}
              onClick={() =>
                interactions
                  ? interactions.onSegmentToAddClicked(segmentId)
                  : () => {}
              }
            >
              {buildLabel(TypeEnum.Dynamic, segmentId)}
            </Badge>
          </Fragment>
        ))}
        {segmentData.dynamicSegmentNamesSubtractive.map((segmentId) => (
          <Fragment key={segmentId}>
            <OperatorBadge text="-" />
            <Badge
              style={segmentStyle}
              onClick={() =>
                interactions
                  ? interactions.onSegmentToRemoveClicked(segmentId)
                  : () => {}
              }
            >
              {buildLabel(TypeEnum.Dynamic, segmentId)}
            </Badge>
          </Fragment>
        ))}
        {segmentData.staticSegmentIdsAdditive.map((segmentId, idx) => (
          <Fragment key={segmentId}>
            {(segmentData.staticSegmentIdsAdditive.length > 0 || idx > 0) && (
              <OperatorBadge text="+" />
            )}
            <Badge
              style={segmentStyle}
              onClick={() =>
                interactions
                  ? interactions.onStaticSegmentToAddClicked(segmentId)
                  : () => {}
              }
            >
              {buildLabel(TypeEnum.Static, segmentId)}
            </Badge>
          </Fragment>
        ))}
        {segmentData.staticSegmentIdsSubtractive?.map((segmentId, idx) => (
          <Fragment key={segmentId}>
            {(segmentData.staticSegmentIdsSubtractive.length > 0 ||
              idx > 0) && <OperatorBadge text="-" />}
            <Badge
              style={segmentStyle}
              onClick={() =>
                interactions
                  ? interactions.onStaticSegmentToRemoveClicked(segmentId)
                  : () => {}
              }
            >
              {buildLabel(TypeEnum.Static, segmentId)}
            </Badge>
          </Fragment>
        ))}
        {segmentData.mailCategoryIdsAdditive.map((mailCategoryId, idx) => (
          <Fragment key={mailCategoryId}>
            {(segmentData.dynamicSegmentNamesAdditive.length > 0 ||
              idx > 0) && <OperatorBadge text="+" />}
            <Badge
              style={segmentStyle}
              onClick={() =>
                interactions
                  ? interactions.onMailCategoryIdClicked(mailCategoryId)
                  : () => {}
              }
            >
              {buildLabel(TypeEnum.Category, mailCategoryId)}
            </Badge>
          </Fragment>
        ))}
      </h6>
    </div>
  );
};

interface OperatorProps {
  text: string;
}
const OperatorBadge: React.FC<OperatorProps> = ({ text }) => {
  return (
    <Badge bg="dark" style={{ userSelect: "none" }}>
      {text}
    </Badge>
  );
};

export default SegmentsDisplay;
