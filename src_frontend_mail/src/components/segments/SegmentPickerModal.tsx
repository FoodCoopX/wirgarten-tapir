import { MinusCircleIcon, PlusCircleIcon } from "@heroicons/react/24/outline";
import React, { useMemo, useState } from "react";
import { Accordion, Form, ListGroup, Modal } from "react-bootstrap";
import { SegmentOption } from "tapir-api-client";

interface SegmentPickerModalProps {
  show: boolean;
  onHide: () => void;
  options: SegmentOption[];
  onAdd: (option: SegmentOption) => void;
  onSubtract?: (option: SegmentOption) => void;
  canSubtract?: (option: SegmentOption) => boolean;
  title?: string;
}

function groupOptions(options: SegmentOption[]) {
  const groups = new Map<string, SegmentOption[]>();
  for (const option of options) {
    groups.set(option.group, [...(groups.get(option.group) ?? []), option]);
  }

  return Array.from(groups.entries()).sort(([groupA], [groupB]) =>
    groupA.localeCompare(groupB),
  );
}

function matchesSearch(option: SegmentOption, search: string) {
  const text = `${option.label} ${option.description} ${option.group}`;
  return text.toLowerCase().includes(search.toLowerCase());
}

const SegmentPickerModal: React.FC<SegmentPickerModalProps> = ({
  show,
  onHide,
  options,
  onAdd,
  onSubtract,
  canSubtract,
  title = "Segment hinzufügen",
}) => {
  const [search, setSearch] = useState("");

  const groups = useMemo(
    () =>
      groupOptions(
        options.filter((option) => matchesSearch(option, search.trim())),
      ),
    [options, search],
  );

  const expandedGroups = search.trim() ? groups.map(([group]) => group) : [];

  function close() {
    setSearch("");
    onHide();
  }

  function buildActionIcon(
    Icon: typeof PlusCircleIcon,
    color: string,
    title: string,
    onClick: () => void,
  ) {
    return (
      <button
        type="button"
        className="btn btn-link p-0"
        title={title}
        aria-label={title}
        onClick={() => {
          onClick();
          close();
        }}
      >
        <Icon color={color} width="2em" />
      </button>
    );
  }

  return (
    <Modal show={show} onHide={close} size="lg" scrollable>
      <Modal.Header closeButton>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form.Control
          type="search"
          placeholder="Suchen …"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          autoFocus
          className="mb-3"
        />
        {groups.length === 0 && <p>Kein Segment gefunden.</p>}
        <Accordion
          alwaysOpen
          defaultActiveKey={expandedGroups}
          key={search.trim()}
        >
          {groups.map(([group, groupOptions]) => (
            <Accordion.Item key={group} eventKey={group}>
              <Accordion.Header>
                {group} ({groupOptions.length})
              </Accordion.Header>
              <Accordion.Body className="p-0">
                <ListGroup variant="flush">
                  {groupOptions.map((option) => (
                    <ListGroup.Item
                      key={option.type + option.id}
                      className="d-flex align-items-center gap-2"
                    >
                      <div className="flex-grow-1">
                        <div>{option.label}</div>
                        {option.description && (
                          <small className="text-muted">
                            {option.description}
                          </small>
                        )}
                      </div>
                      {buildActionIcon(
                        PlusCircleIcon,
                        "green",
                        "Hinzufügen",
                        () => onAdd(option),
                      )}
                      {onSubtract &&
                        (canSubtract?.(option) ?? true) &&
                        buildActionIcon(
                          MinusCircleIcon,
                          "red",
                          "Abziehen",
                          () => onSubtract(option),
                        )}
                    </ListGroup.Item>
                  ))}
                </ListGroup>
              </Accordion.Body>
            </Accordion.Item>
          ))}
        </Accordion>
      </Modal.Body>
    </Modal>
  );
};

export default SegmentPickerModal;
