import { FC, useEffect, useState } from "react";
import { Accordion, Badge, Button, Form } from "react-bootstrap";
import {
  SegmentData,
  SegmentOption,
  TapirmailApi,
  TypeEnum,
} from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import SegmentsDisplay from "../segmentsDisplay";
import SegmentPickerModal from "./SegmentPickerModal";

type SegmentInputProps = {
  initialData?: SegmentData;
  onChange: (data: SegmentData) => void;
};

const SegmentInput: FC<SegmentInputProps> = ({ initialData, onChange }) => {
  const segmentApi = useApi(TapirmailApi);
  const showAlert = useAlert();

  const [availableSegments, setAvailableSegments] = useState<SegmentOption[]>(
    [],
  );
  const [segmentPickerOpen, setSegmentPickerOpen] = useState(false);

  const [segmentsToAdd, setSegmentsToAdd] = useState<string[]>([]);
  const [staticSegmentsToAdd, setStaticSegmentsToAdd] = useState<string[]>([]);
  const [staticSegmentsToRemove, setStaticSegmentsToRemove] = useState<
    string[]
  >([]);
  const [segmentsToRemove, setSegmentsToRemove] = useState<string[]>([]);
  const [selectedMailCategoryIds, setSelectedMailCategoryIds] = useState<
    string[]
  >([]);

  const [resultCount, setResultCount] = useState<number>(0);
  const [resultRecipients, setResultRecipients] = useState<any[]>([]);

  useEffect(() => {
    onChange({
      dynamicSegmentNamesAdditive: segmentsToAdd,
      dynamicSegmentNamesSubtractive: segmentsToRemove,
      staticSegmentIdsAdditive: staticSegmentsToAdd,
      staticSegmentIdsSubtractive: staticSegmentsToRemove,
      mailCategoryIdsAdditive: selectedMailCategoryIds,
    });
  }, [
    segmentsToAdd,
    staticSegmentsToAdd,
    segmentsToRemove,
    staticSegmentsToRemove,
    selectedMailCategoryIds,
  ]);

  useEffect(() => {
    segmentApi
      .tapirmailApiSegmentAvailableSegmentsRetrieve()
      .then((response) => {
        setAvailableSegments(response.segments);

        if (initialData) {
          setSegmentsToAdd(initialData.dynamicSegmentNamesAdditive);
          setSegmentsToRemove(initialData.dynamicSegmentNamesSubtractive);
          setStaticSegmentsToAdd(initialData.staticSegmentIdsAdditive);
          setStaticSegmentsToRemove(
            initialData.staticSegmentIdsSubtractive ?? [],
          );
          setSelectedMailCategoryIds(initialData.mailCategoryIdsAdditive ?? []);
        }
      })
      .catch((err) => {
        console.error(err);
        showAlert("Fehler beim laden der Segmente!", "danger");
      });
  }, []);

  useEffect(() => {
    if (
      segmentsToAdd.length +
        staticSegmentsToAdd.length +
        selectedMailCategoryIds.length <
      1
    ) {
      return;
    }

    segmentApi
      .tapirmailApiSegmentCombineCreate({
        segmentDataRequest: {
          dynamicSegmentNamesAdditive: segmentsToAdd,
          dynamicSegmentNamesSubtractive: segmentsToRemove,
          staticSegmentIdsAdditive: staticSegmentsToAdd,
          staticSegmentIdsSubtractive: staticSegmentsToRemove,
          mailCategoryIdsAdditive: selectedMailCategoryIds,
        },
      })
      .then(({ count, recipients }) => {
        setResultCount(count!);
        setResultRecipients(recipients!.map((recipient) => recipient.name));
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim Laden der Empfänger!", "danger");
      });
  }, [
    segmentsToAdd,
    staticSegmentsToAdd,
    staticSegmentsToRemove,
    segmentsToRemove,
    selectedMailCategoryIds,
  ]);

  const handleAddSegment = (option: SegmentOption) => {
    switch (option.type) {
      case TypeEnum.Static:
        setStaticSegmentsToAdd((previous) => [...previous, option.id]);
        break;
      case TypeEnum.Category:
        setSelectedMailCategoryIds((previous) => [...previous, option.id]);
        break;
      default:
        setSegmentsToAdd((previous) => [...previous, option.id]);
    }
  };

  const handleSubtractSegment = (option: SegmentOption) => {
    if (option.type === TypeEnum.Static) {
      setStaticSegmentsToRemove((previous) => [...previous, option.id]);
    } else {
      setSegmentsToRemove((previous) => [...previous, option.id]);
    }
  };

  const canSubtractSegment = (option: SegmentOption) =>
    option.type !== TypeEnum.Category && segmentsToAdd.length > 0;

  const alreadyUsedIds: { [type: string]: string[] } = {
    [TypeEnum.Dynamic]: [...segmentsToAdd, ...segmentsToRemove],
    [TypeEnum.Static]: [...staticSegmentsToAdd, ...staticSegmentsToRemove],
    [TypeEnum.Category]: selectedMailCategoryIds,
  };
  const pickableSegments = availableSegments.filter(
    (option) => !alreadyUsedIds[option.type].includes(option.id),
  );

  function onSegmentToAddClicked(segment: string) {
    const newSegmentsToAdd = segmentsToAdd.filter((s) => s !== segment);
    setSegmentsToAdd(newSegmentsToAdd);
    if (newSegmentsToAdd.length === 0) {
      setSegmentsToRemove([]);
    }
  }

  function onSegmentToRemoveClicked(segment: string) {
    setSegmentsToRemove(segmentsToRemove.filter((s) => s !== segment));
  }

  function onStaticSegmentToAddClicked(segment: string) {
    setStaticSegmentsToAdd(staticSegmentsToAdd.filter((s) => s !== segment));
  }

  function onStaticSegmentToRemoveClicked(segment: string) {
    setStaticSegmentsToRemove(staticSegmentsToAdd.filter((s) => s !== segment));
  }

  function onMailCategoryIdClicked(mailCategoryId: string) {
    setSelectedMailCategoryIds(
      selectedMailCategoryIds.filter((id) => id !== mailCategoryId),
    );
  }

  const hasSegments =
    segmentsToAdd.length > 0 ||
    staticSegmentsToAdd.length > 0 ||
    selectedMailCategoryIds.length > 0;

  return (
    <div>
      <Form.Label className="d-block">Segmente</Form.Label>
      {!hasSegments && (
        <div className="text-muted mb-2">Kein Segment ausgewählt</div>
      )}
      <SegmentsDisplay
        segmentData={{
          dynamicSegmentNamesAdditive: segmentsToAdd,
          dynamicSegmentNamesSubtractive: segmentsToRemove,
          staticSegmentIdsAdditive: staticSegmentsToAdd,
          staticSegmentIdsSubtractive: staticSegmentsToRemove,
          mailCategoryIdsAdditive: selectedMailCategoryIds,
        }}
        interactions={{
          onSegmentToAddClicked: onSegmentToAddClicked,
          onSegmentToRemoveClicked: onSegmentToRemoveClicked,
          onStaticSegmentToAddClicked: onStaticSegmentToAddClicked,
          onStaticSegmentToRemoveClicked: onStaticSegmentToRemoveClicked,
          onMailCategoryIdClicked: onMailCategoryIdClicked,
        }}
        availableSegments={availableSegments}
      />
      <Button
        variant="outline-primary"
        onClick={() => setSegmentPickerOpen(true)}
      >
        Segment hinzufügen
      </Button>
      <SegmentPickerModal
        show={segmentPickerOpen}
        onHide={() => setSegmentPickerOpen(false)}
        options={pickableSegments}
        onAdd={handleAddSegment}
        onSubtract={handleSubtractSegment}
        canSubtract={canSubtractSegment}
      />

      {hasSegments && (
        <Accordion style={{ marginTop: "1em" }}>
          <Accordion.Item eventKey="0">
            <Accordion.Header>
              <span style={{ width: "100%" }}>
                Empfänger&nbsp;
                <Badge
                  style={{ float: "right", marginRight: "1em" }}
                  bg="success"
                >
                  {resultCount}
                </Badge>
              </span>
            </Accordion.Header>
            <Accordion.Body className="p-0" style={{ textAlign: "left" }}>
              {resultRecipients.map((recipient, idx) => (
                <span
                  key={recipient}
                  className={`d-block ${
                    idx % 2 === 0 ? "bg-light" : ""
                  } py-1 px-2`}
                >
                  <small>
                    <strong>{idx + 1}: </strong>
                    {recipient}
                  </small>
                </span>
              ))}
            </Accordion.Body>
          </Accordion.Item>
        </Accordion>
      )}
    </div>
  );
};

export default SegmentInput;
