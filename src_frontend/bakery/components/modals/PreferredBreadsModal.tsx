import React, { useEffect, useState } from "react";
import { Modal } from "react-bootstrap";
import { InfoCircle, StarFill } from "react-bootstrap-icons";
import { BakeryApi } from "../../../api-client";
import type {
  BreadContent,
  BreadLabel,
  BreadList,
} from "../../../api-client/models";
import TapirButton from "../../../components/TapirButton";
import { useApi } from "../../../hooks/useApi";
import { handleRequestError } from "../../../utils/handleRequestError";
import "../../styles/bakery_styles.css";
import { SingleBreadCard } from "../cards";

interface PreferredBreadsModalProps {
  isOpen: boolean;
  onClose: () => void;
  memberId: string;
  csrfToken: string;
}

// Mirrors MAX_PREFERRED_BREADS in tapir/bakery/utils.py, which the API now
// enforces. Keep the two in step: the server answers 400 above its own limit.
const MAX_PREFERRED_BREADS = 3;

export const PreferredBreadsModal: React.FC<PreferredBreadsModalProps> = ({
  isOpen,
  onClose,
  memberId,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [breads, setBreads] = useState<BreadList[]>([]);
  const [labelsMap, setLabelsMap] = useState<{ [labelId: string]: BreadLabel }>(
    {},
  );
  const [contentsMap, setContentsMap] = useState<{
    [breadId: string]: BreadContent[];
  }>({});
  const [selectedBreadIds, setSelectedBreadIds] = useState<Set<string>>(
    new Set(),
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [limitReached, setLimitReached] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, memberId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Not while loading, or Enter would POST a selection that has not been
      // read back yet and wipe the member's saved favourites.
      if (e.key === "Enter" && !saving && !loading) {
        e.preventDefault();
        handleSave();
      }
    };

    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, saving, loading, selectedBreadIds]);

  const loadData = () => {
    // The component stays mounted between openings, so every piece of
    // per-opening state has to be reset here: a stale refusal message greeted
    // the next visitor, and an unsaved selection survived "Abbrechen".
    setLimitReached(false);
    setSelectedBreadIds(new Set());
    setLoading(true);
    Promise.all([
      bakeryApi.bakeryBreadsListList({}),
      bakeryApi.bakeryPreferredBreadsList({ memberId }),
      bakeryApi.bakeryLabelsList(),
      bakeryApi.bakeryBreadcontentsList(),
    ])
      .then(([breadsData, preferredData, labels, contents]) => {
        setBreads(breadsData.filter((b) => b.isActive !== false));

        const labelMapping = labels.reduce(
          (acc, label) => {
            if (label.id) {
              acc[label.id] = label;
            }
            return acc;
          },
          {} as { [labelId: string]: BreadLabel },
        );
        setLabelsMap(labelMapping);

        const contentMapping = contents.reduce(
          (acc, content) => {
            const breadId = content.bread;
            if (breadId) {
              if (!acc[breadId]) {
                acc[breadId] = [];
              }
              acc[breadId].push(content);
            }
            return acc;
          },
          {} as { [breadId: string]: BreadContent[] },
        );
        setContentsMap(contentMapping);

        // Unconditional: a member with no saved favourites must end up with
        // an empty set, not with whatever was left from the last opening.
        setSelectedBreadIds(new Set(preferredData[0]?.breads ?? []));
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Laden der Brote");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const toggleBread = (breadId: string) => {
    const newSelected = new Set(selectedBreadIds);

    if (newSelected.has(breadId)) {
      newSelected.delete(breadId);
      setLimitReached(false);
      setSelectedBreadIds(newSelected);
      return;
    }

    // Refuse the pick rather than evicting one of the existing favourites,
    // which the member would have no way of noticing.
    if (newSelected.size >= MAX_PREFERRED_BREADS) {
      setLimitReached(true);
      return;
    }

    newSelected.add(breadId);
    setLimitReached(false);
    setSelectedBreadIds(newSelected);
  };
  const handleSave = () => {
    setSaving(true);
    bakeryApi
      .bakeryPreferredBreadsBulkUpdateCreate({
        id: memberId,
        preferredBreadsBulkUpdateRequest: {
          breads: Array.from(selectedBreadIds),
        },
      })
      .then(() => {
        onClose();
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Speichern der Lieblingsbrote");
      })
      .finally(() => {
        setSaving(false);
      });
  };

  return (
    <Modal show={isOpen} onHide={onClose} size="xl" scrollable>
      <Modal.Header closeButton className="header-white-on-middle-brown">
        <Modal.Title>
          <h5 className="mb-0">
            <StarFill size={20} className="me-2" />
            Lieblingsbrote auswählen
          </h5>
        </Modal.Title>
      </Modal.Header>

      <Modal.Body className="p-4">
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border spinner-bakery-primary" />
            <p className="mt-2 text-muted">Lade Brote...</p>
          </div>
        ) : breads.length === 0 ? (
          <div
            className="alert alert-info d-flex align-items-center"
            role="alert"
          >
            <InfoCircle size={20} className="me-2" />
            Keine Brote verfügbar.
          </div>
        ) : (
          <>
            <div
              className="alert alert-light d-flex align-items-start mb-4"
              role="alert"
            >
              <InfoCircle
                size={20}
                className="me-2 mt-1 icon-bakery-primary-darker"
                style={{ color: "var(--bakery-brown-medium)" }}
              />
              <div>
                <strong>
                  Wähle bis zu {MAX_PREFERRED_BREADS} Lieblingsbrote aus
                </strong>
                <p className="mb-0 small text-muted">
                  Wir versuchen die Abhol-Orte so mit möglichst vielen
                  Lieblingsbroten zu bestücken.
                </p>
              </div>
            </div>

            <div className="d-flex flex-wrap gap-3">
              {breads.map((bread) => {
                const isSelected = selectedBreadIds.has(bread.id!);
                const breadLabels = (bread.labels || [])
                  .map((labelId) => labelsMap[labelId])
                  .filter(Boolean);

                const breadContents = contentsMap[bread.id!] || [];

                return (
                  <SingleBreadCard
                    key={bread.id}
                    bread={bread}
                    contents={breadContents}
                    labels={breadLabels}
                    isPreferred={isSelected}
                    onClick={() => toggleBread(bread.id!)}
                    footerText={isSelected ? "Lieblingsbrot" : "Auswählen"}
                  />
                );
              })}
            </div>
          </>
        )}
      </Modal.Body>

      <Modal.Footer>
        <div className="me-auto small">
          <span className="text-muted">
            {selectedBreadIds.size} / {MAX_PREFERRED_BREADS}{" "}
            {selectedBreadIds.size === 1 ? "Brot" : "Brote"} ausgewählt
          </span>
          {limitReached && (
            <div className="text-danger">
              Entferne zuerst ein Brot, um ein anderes auszuwählen.
            </div>
          )}
        </div>
        <TapirButton
          variant="secondary"
          text="Abbrechen"
          onClick={onClose}
          disabled={saving}
        />
        <TapirButton
          variant=""
          className="dark-brown-button"
          text="Speichern"
          icon="save"
          onClick={handleSave}
          loading={saving}
          disabled={loading}
        />
      </Modal.Footer>
    </Modal>
  );
};
