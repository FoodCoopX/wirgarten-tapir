import React, { useEffect, useState } from "react";
import { Alert, Form, Modal, Spinner } from "react-bootstrap";
import {
  AdminStartDateOptions,
  AdminSubscriptionAdditionRequest,
  AdminSubscriptionChangeMemberData,
  PickupLocationsApi,
  Product,
  PublicPickupLocation,
  SubscriptionsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import AdminSubscriptionAdditionSummary from "./AdminSubscriptionAdditionSummary.tsx";
import MemberSearchInput from "./MemberSearchInput.tsx";
import MemberSubscriptionPrerequisitesCard from "./MemberSubscriptionPrerequisitesCard.tsx";
import SubscriptionStartDateOptions from "./SubscriptionStartDateOptions.tsx";
import { SubscriptionPrerequisitesFormData } from "./types/SubscriptionPrerequisitesFormData.ts";
import { isSubscriptionPrerequisitesFormComplete } from "./utils/isSubscriptionPrerequisitesFormComplete.ts";

type Step = "member" | "addition" | "summary";

type CheckResult = "pending" | "passed" | { error: string };

const CHECK_DELAY_MS = 300;

const EMPTY_PREREQUISITES: SubscriptionPrerequisitesFormData = {
  pickupLocationId: undefined,
  accountOwner: "",
  iban: "",
  sepaMandateConfirmed: false,
};

const HELP_TEXT = (
  <>
    <p>
      Fügt einen neuen Vertrag zusätzlich zu den bestehenden Verträgen des
      Mitglieds hinzu. Bestehende Verträge werden nicht verändert.
    </p>
    <p className={"mb-0"}>
      Der neue Vertrag wird direkt bestätigt und das Mitglied erhält die Mail,
      die für den Trigger „Vertragsänderungen im Mitgliederbereich“ hinterlegt
      ist.
    </p>
  </>
);

interface AdminSubscriptionAdditionModalProps {
  onHide: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const AdminSubscriptionAdditionModal: React.FC<
  AdminSubscriptionAdditionModalProps
> = ({ onHide, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi);
  const pickupLocationsApi = useApi(PickupLocationsApi);

  const [step, setStep] = useState<Step>("member");
  const [products, setProducts] = useState<Product[]>([]);
  const [pickupLocations, setPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [memberId, setMemberId] = useState<string>();
  const [memberData, setMemberData] =
    useState<AdminSubscriptionChangeMemberData>();
  const [productTypeId, setProductTypeId] = useState<string>();
  const [dateOptions, setDateOptions] = useState<AdminStartDateOptions>();
  const [productId, setProductId] = useState<string>();
  const [quantity, setQuantity] = useState(1);
  const [startDate, setStartDate] = useState<string>();
  const [prerequisites, setPrerequisites] =
    useState<SubscriptionPrerequisitesFormData>(EMPTY_PREREQUISITES);
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<CheckResult>("pending");
  const [saving, setSaving] = useState(false);

  const availableProducts = products.filter((product) => !product.deleted);
  const productTypes = [
    ...new Map(
      availableProducts.map((product) => [product.type.id, product.type]),
    ).values(),
  ];
  const existingUnitsOfType =
    memberData?.subscriptionUnits.filter(
      (unit) => unit.productTypeId === productTypeId && unit.status !== "ended",
    ) ?? [];
  const productAlreadySubscribed = existingUnitsOfType.some(
    (unit) => unit.productId === productId,
  );
  const prerequisitesComplete =
    memberData !== undefined &&
    isSubscriptionPrerequisitesFormComplete(
      memberData.prerequisites,
      prerequisites,
    );

  useEffect(() => {
    subscriptionsApi
      .subscriptionsProductsList()
      .then(setProducts)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Anteilsgrößen",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    setMemberData(undefined);
    setPrerequisites(EMPTY_PREREQUISITES);
    if (!memberId) return;

    subscriptionsApi
      .subscriptionsApiAdminSubscriptionChangeMemberDataRetrieve({ memberId })
      .then((data) => {
        setMemberData(data);
        if (data.prerequisites.pickupLocationName === null) {
          return pickupLocationsApi
            .pickupLocationsPublicPickupLocationsList()
            .then(setPickupLocations);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mitgliedsdaten",
          setToastDatas,
        ),
      );
  }, [memberId]);

  useEffect(() => {
    setDateOptions(undefined);
    setProductId(undefined);
    setStartDate(undefined);
    if (!productTypeId) return;

    subscriptionsApi
      .subscriptionsApiAdminSubscriptionAdditionDateOptionsRetrieve({
        productTypeId,
      })
      .then(setDateOptions)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Datumsoptionen",
          setToastDatas,
        ),
      );
  }, [productTypeId]);

  useEffect(() => {
    setCheckResult("pending");
    if (!productId || !startDate || quantity < 1 || !prerequisitesComplete)
      return;

    let cancelled = false;
    const timeout = setTimeout(() => {
      setChecking(true);
      subscriptionsApi
        .subscriptionsApiAdminSubscriptionAdditionCheckCreate({
          adminSubscriptionAdditionRequest: buildRequest(),
        })
        .then((response) => {
          if (!cancelled) {
            setCheckResult(
              response.orderConfirmed
                ? "passed"
                : { error: response.error ?? "" },
            );
          }
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler bei der Prüfung des Vertrags",
            setToastDatas,
          ),
        )
        .finally(() => {
          if (!cancelled) setChecking(false);
        });
    }, CHECK_DELAY_MS);

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [productId, quantity, startDate, prerequisites, prerequisitesComplete]);

  function buildRequest(): AdminSubscriptionAdditionRequest {
    return {
      memberId: memberId!,
      productId: productId!,
      quantity,
      startDate: startDate!,
      prerequisites,
    };
  }

  function onSave() {
    setSaving(true);
    subscriptionsApi
      .subscriptionsApiAdminSubscriptionAdditionApplyCreate({
        adminSubscriptionAdditionRequest: buildRequest(),
      })
      .then((response) => {
        if (response.orderConfirmed) {
          globalThis.location.reload();
          return;
        }
        setCheckResult({ error: response.error ?? "" });
        setStep("addition");
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern des Vertrags",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function renderExistingUnitsWarning() {
    if (productAlreadySubscribed) {
      return (
        <Alert variant={"danger"} className={"mb-0"}>
          Dieses Mitglied hat bereits einen Vertrag für diese Anteilsgröße. Um
          die Anzahl der Anteile zu ändern, wende dich bitte an die
          FoodCoopX-Admins.
        </Alert>
      );
    }

    if (existingUnitsOfType.length === 0) {
      return null;
    }

    return (
      <Alert variant={"warning"} className={"mb-0"}>
        <p>Dieses Mitglied hat bereits Verträge dieses Produktanteils:</p>
        <ul>
          {existingUnitsOfType.map((unit) => (
            <li key={`${unit.subscriptionId}_${unit.unitNumber}`}>
              {unit.productName}, {formatDateNumeric(unit.startDate)} –{" "}
              {formatDateNumeric(unit.endDate)}
            </li>
          ))}
        </ul>
        <p className={"mb-0"}>
          Der neue Vertrag kommt zusätzlich hinzu. Um einen bestehenden Vertrag
          zu verändern, nutze stattdessen "Anteilsgröße ändern",
          "Vertragsstart-anpassen/Sonderkündigung" oder "Betrag ändern".
        </p>
      </Alert>
    );
  }

  function renderAdditionStep() {
    if (!memberData) {
      return <Spinner />;
    }

    return (
      <div className={"d-flex flex-column gap-3"}>
        <Form.Group>
          <Form.Label>Produktanteil</Form.Label>
          <Form.Select
            value={productTypeId ?? ""}
            onChange={(event) =>
              setProductTypeId(event.target.value || undefined)
            }
          >
            <option value={""}>Produktanteil auswählen</option>
            {productTypes.map((productType) => (
              <option key={productType.id} value={productType.id}>
                {productType.name}
              </option>
            ))}
          </Form.Select>
        </Form.Group>
        {productTypeId && !dateOptions && <Spinner />}
        {dateOptions && (
          <>
            <div className={"d-flex flex-row gap-3"}>
              <Form.Group className={"flex-grow-1"}>
                <Form.Label>Anteilsgröße</Form.Label>
                <Form.Select
                  value={productId ?? ""}
                  onChange={(event) =>
                    setProductId(event.target.value || undefined)
                  }
                >
                  <option value={""}>Anteilsgröße auswählen</option>
                  {availableProducts
                    .filter((product) => product.type.id === productTypeId)
                    .map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name}
                      </option>
                    ))}
                </Form.Select>
              </Form.Group>
              <Form.Group>
                <Form.Label>Anzahl</Form.Label>
                <Form.Control
                  type={"number"}
                  min={1}
                  value={quantity}
                  onChange={(event) => setQuantity(Number(event.target.value))}
                />
              </Form.Group>
            </div>
            {renderExistingUnitsWarning()}
            <Form.Group>
              <Form.Label>Vertragsbeginn</Form.Label>
              <SubscriptionStartDateOptions
                nextPossibleStart={dateOptions.nextPossibleStart}
                weeks={dateOptions.weeks}
                nextPeriodStart={dateOptions.nextPeriodStart}
                selectedDate={startDate}
                setSelectedDate={setStartDate}
              />
            </Form.Group>
          </>
        )}
        <MemberSubscriptionPrerequisitesCard
          status={memberData.prerequisites}
          pickupLocations={pickupLocations}
          formData={prerequisites}
          setFormData={setPrerequisites}
          showValidation={false}
        />
        {checking && <Spinner size={"sm"} />}
        {typeof checkResult === "object" && (
          <Alert variant={"danger"}>{checkResult.error}</Alert>
        )}
      </div>
    );
  }

  function renderSummaryStep() {
    const product = products.find((product) => product.id === productId);
    if (!memberData || !product || !startDate) {
      return <Spinner />;
    }

    return (
      <AdminSubscriptionAdditionSummary
        memberData={memberData}
        product={product}
        quantity={quantity}
        startDate={startDate}
        prerequisites={prerequisites}
        pickupLocationName={
          memberData.prerequisites.pickupLocationName ??
          pickupLocations.find(
            (location) => location.id === prerequisites.pickupLocationId,
          )?.name
        }
      />
    );
  }

  function renderFooter() {
    switch (step) {
      case "member":
        return (
          <TapirButton
            variant={"primary"}
            icon={"arrow_forward"}
            text={"Weiter"}
            disabled={!memberData}
            onClick={() => setStep("addition")}
          />
        );
      case "addition":
        return (
          <>
            <TapirButton
              variant={"outline-secondary"}
              icon={"arrow_back"}
              text={"Zurück"}
              onClick={() => setStep("member")}
            />
            <TapirButton
              variant={"primary"}
              icon={"arrow_forward"}
              text={"Weiter"}
              disabled={checking || checkResult !== "passed"}
              onClick={() => setStep("summary")}
            />
          </>
        );
      case "summary":
        return (
          <>
            <TapirButton
              variant={"outline-secondary"}
              icon={"arrow_back"}
              text={"Zurück"}
              onClick={() => setStep("addition")}
            />
            <TapirButton
              variant={"primary"}
              icon={"save"}
              text={"Speichern"}
              loading={saving}
              onClick={onSave}
            />
          </>
        );
    }
  }

  return (
    <Modal show onHide={onHide} centered size={"lg"}>
      <Modal.Header closeButton>
        <div className={"d-flex flex-row gap-2 align-items-center"}>
          <h5 className={"mb-0"}>Vertrag hinzufügen</h5>
          <TapirHelpButton text={HELP_TEXT} />
        </div>
      </Modal.Header>
      <Modal.Body>
        {step === "member" && (
          <MemberSearchInput
            memberId={memberId}
            memberSummary={memberData?.member}
            setMemberId={setMemberId}
            setToastDatas={setToastDatas}
          />
        )}
        {step === "addition" && renderAdditionStep()}
        {step === "summary" && renderSummaryStep()}
      </Modal.Body>
      <Modal.Footer>{renderFooter()}</Modal.Footer>
    </Modal>
  );
};

export default AdminSubscriptionAdditionModal;
