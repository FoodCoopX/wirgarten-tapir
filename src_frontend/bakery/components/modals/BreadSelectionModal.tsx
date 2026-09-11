import React, { useEffect, useState } from "react";
import { Modal } from "react-bootstrap";
import { BakeryApi } from "../../../api-client";
import type {
  BreadContent,
  BreadLabel,
  BreadList,
} from "../../../api-client/models";
import { useApi } from "../../../hooks/useApi";
import { handleRequestError } from "../../../utils/handleRequestError";
import "../../styles/bakery_styles.css";
import { SingleBreadCard } from "../cards";

interface BreadSelectionModalProps {
  contentsMap: { [breadId: string]: BreadContent[] };
  pickupLocationId: string;
  pickupLocationName: string;
  selectedWeek: number;
  selectedYear: number;
  currentBreadId?: string | null;
  onSelect: (breadId: string) => void;
  onClose: () => void;
  csrfToken: string;
}

export const BreadSelectionModal: React.FC<BreadSelectionModalProps> = ({
  contentsMap,
  pickupLocationId,
  pickupLocationName,
  selectedWeek,
  selectedYear,
  currentBreadId,
  onSelect,
  onClose,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [availableBreads, setAvailableBreads] = useState<BreadList[]>([]);
  const [labelsMap, setLabelsMap] = useState<{ [labelId: string]: BreadLabel }>(
    {},
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [pickupLocationId, selectedWeek, selectedYear]);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      bakeryApi.bakeryBreadsListList({
        isActive: true,
        pickupLocationId,
        year: selectedYear,
        week: selectedWeek,
      }),
      bakeryApi.bakeryLabelsList(),
    ])
      .then(([breadsWithCapacity, labels]) => {
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
        setAvailableBreads(breadsWithCapacity);
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Laden der Brote");
        setAvailableBreads([]);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <Modal show onHide={onClose} size="xl" scrollable centered>
      <Modal.Header closeButton className="header-darkbrown-on-sahara">
        <Modal.Title>Brot auswählen für {pickupLocationName}</Modal.Title>
      </Modal.Header>

      <Modal.Body className="modal-body-bakery">
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border spinner-bakery" />
            <p className="mt-2 text-muted">Lade verfügbare Brote...</p>
          </div>
        ) : (
          <>
            <div className="alert alert-info mb-4">
              <strong>
                KW {selectedWeek}/{selectedYear}
              </strong>{" "}
              - Station: {pickupLocationName}
              <br />
              <small>
                {availableBreads.length} Brotsorte
                {availableBreads.length !== 1 ? "n" : ""} verfügbar
              </small>
            </div>

            {availableBreads.length === 0 ? (
              <div className="alert alert-warning">
                <strong>Keine Brote verfügbar</strong>
                <p className="mb-0">
                  Für diese Abholstation und Woche sind noch keine Brote mit
                  verfügbarer Kapazität vorhanden.
                </p>
              </div>
            ) : (
              <div className="d-flex flex-wrap gap-3">
                {availableBreads.map((bread) => {
                  const contents = contentsMap[bread.id!] || [];
                  const breadLabels = (bread.labels || [])
                    .map((labelId) => labelsMap[labelId])
                    .filter(Boolean);
                  const isSelected = bread.id === currentBreadId;

                  return (
                    <SingleBreadCard
                      key={bread.id}
                      bread={bread}
                      contents={contents}
                      labels={breadLabels}
                      isSelected={isSelected}
                      onClick={() => onSelect(bread.id!)}
                      showAvailability={true}
                    />
                  );
                })}
              </div>
            )}
          </>
        )}
      </Modal.Body>
    </Modal>
  );
};
