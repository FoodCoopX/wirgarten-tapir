import React, { useEffect, useState } from "react";
import { Alert, Form, Modal, Spinner } from "react-bootstrap";
import {
  AdminSizeChangeDateOptions,
  AdminSizeChangeRequestRequest,
  AdminSubscriptionChangeMemberData,
  AdminSubscriptionChangeSubscriptionUnit,
  PickupLocationsApi,
  Product,
  PublicPickupLocation,
  SubscriptionsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import AdminSizeChangeSummary from "./AdminSizeChangeSummary.tsx";
import MemberSearchInput from "./MemberSearchInput.tsx";
import MemberSubscriptionPrerequisitesCard from "./MemberSubscriptionPrerequisitesCard.tsx";
import SubscriptionStartDateOptions from "./SubscriptionStartDateOptions.tsx";
import SubscriptionUnitList from "./SubscriptionUnitList.tsx";
import { SubscriptionPrerequisitesFormData } from "./types/SubscriptionPrerequisitesFormData.ts";
import { isSubscriptionPrerequisitesFormComplete } from "./utils/isSubscriptionPrerequisitesFormComplete.ts";
import { isSubscriptionUnitEditable } from "./utils/isSubscriptionUnitEditable.ts";

type Step = "member" | "change" | "summary";

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
      Ersetzt einen Anteil durch eine andere Produktanteilsgröße derselben
      Vertragsart, ab einem bestimmten Datum.
    </p>
    <p className={"mb-0"}>
      Der bisherige Vertrag wird als gekündigt markiert, die neuen Verträge
      werden direkt bestätigt und das Mitglied erhält eine Bestätigungsmail.
    </p>
  </>
);

interface AdminSubscriptionChangeModalProps {
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const AdminSubscriptionChangeModal: React.FC<
  AdminSubscriptionChangeModalProps
> = ({ onHide, csrfToken, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const pickupLocationsApi = useApi(PickupLocationsApi, csrfToken);

  const [step, setStep] = useState<Step>("member");
  const [products, setProducts] = useState<Product[]>([]);
  const [pickupLocations, setPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [memberId, setMemberId] = useState<string>();
  const [memberData, setMemberData] =
    useState<AdminSubscriptionChangeMemberData>();
  const [unit, setUnit] = useState<AdminSubscriptionChangeSubscriptionUnit>();
  const [dateOptions, setDateOptions] = useState<AdminSizeChangeDateOptions>();
  const [newProductId, setNewProductId] = useState<string>();
  const [changeDate, setChangeDate] = useState<string>();
  const [prerequisites, setPrerequisites] =
    useState<SubscriptionPrerequisitesFormData>(EMPTY_PREREQUISITES);
  const [checking, setChecking] = useState(false);
  // undefined: not checked yet, null: check passed, string: check failed
  const [checkError, setCheckError] = useState<string | null>();
  const [saving, setSaving] = useState(false);

  const prerequisitesComplete =
    memberData !== undefined &&
    isSubscriptionPrerequisitesFormComplete(
      memberData.prerequisites,
      prerequisites,
    );
  const checkPassed = checkError === null;

  useEffect(() => {
    subscriptionsApi
      .subscriptionsProductsList()
      .then(setProducts)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Produkte",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    setMemberData(undefined);
    setUnit(undefined);
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
    setNewProductId(undefined);
    setChangeDate(undefined);
    if (!unit) return;

    subscriptionsApi
      .subscriptionsApiAdminSizeChangeDateOptionsRetrieve({
        subscriptionId: unit.subscriptionId,
      })
      .then(setDateOptions)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Datumsoptionen",
          setToastDatas,
        ),
      );
  }, [unit]);

  useEffect(() => {
    setCheckError(undefined);
    if (!newProductId || !changeDate || !prerequisitesComplete) return;

    let cancelled = false;
    const timeout = setTimeout(() => {
      setChecking(true);
      subscriptionsApi
        .subscriptionsApiAdminSizeChangeCheckCreate({
          adminSizeChangeRequestRequest: buildRequest(),
        })
        .then((response) => {
          if (!cancelled) setCheckError(response.error);
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler bei der Prüfung der Änderung",
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
  }, [newProductId, changeDate, prerequisites, prerequisitesComplete]);

  function buildRequest(): AdminSizeChangeRequestRequest {
    return {
      memberId: memberId!,
      subscriptionId: unit!.subscriptionId,
      newProductId: newProductId!,
      changeDate: changeDate!,
      pickupLocationId: prerequisites.pickupLocationId ?? null,
      accountOwner: prerequisites.accountOwner,
      iban: prerequisites.iban,
      sepaMandateConfirmed: prerequisites.sepaMandateConfirmed,
    };
  }

  function onSave() {
    setSaving(true);
    subscriptionsApi
      .subscriptionsApiAdminSizeChangeApplyCreate({
        adminSizeChangeRequestRequest: buildRequest(),
      })
      .then((response) => {
        if (response.orderConfirmed) {
          globalThis.location.reload();
          return;
        }
        setCheckError(response.error);
        setStep("change");
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Änderung",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function renderMemberStep() {
    return (
      <div className={"d-flex flex-column gap-3"}>
        <MemberSearchInput
          csrfToken={csrfToken}
          memberId={memberId}
          memberSummary={memberData?.member}
          setMemberId={setMemberId}
          setToastDatas={setToastDatas}
        />
        {memberData && (
          <SubscriptionUnitList
            units={memberData.subscriptionUnits}
            selectedUnit={unit}
            setSelectedUnit={setUnit}
          />
        )}
      </div>
    );
  }

  function renderChangeStep() {
    if (!memberData || !unit || !dateOptions) {
      return <Spinner />;
    }

    const productOptions = products.filter(
      (product) =>
        product.type.id === unit.productTypeId &&
        !product.deleted &&
        product.id !== unit.productId,
    );

    return (
      <div className={"d-flex flex-column gap-3"}>
        <Form.Group>
          <Form.Label>
            Neue Anteilsgröße für {unit.productTypeName} (bisher{" "}
            {unit.productName})
          </Form.Label>
          <Form.Select
            value={newProductId ?? ""}
            onChange={(event) =>
              setNewProductId(event.target.value || undefined)
            }
          >
            <option value={""}>Anteilsgröße auswählen</option>
            {productOptions.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </Form.Select>
        </Form.Group>
        <Form.Group>
          <Form.Label>Wirksam ab</Form.Label>
          <SubscriptionStartDateOptions
            nextPossibleStart={dateOptions.nextPossibleStart}
            weeks={dateOptions.weeks}
            nextPeriodStart={dateOptions.nextPeriodStart}
            selectedDate={changeDate}
            setSelectedDate={setChangeDate}
          />
        </Form.Group>
        <MemberSubscriptionPrerequisitesCard
          status={memberData.prerequisites}
          pickupLocations={pickupLocations}
          formData={prerequisites}
          setFormData={setPrerequisites}
          showValidation={false}
        />
        {checking && <Spinner size={"sm"} />}
        {checkError && <Alert variant={"danger"}>{checkError}</Alert>}
      </div>
    );
  }

  function renderSummaryStep() {
    const newProduct = products.find((product) => product.id === newProductId);
    if (!memberData || !unit || !newProduct || !changeDate) {
      return <Spinner />;
    }

    return (
      <AdminSizeChangeSummary
        memberData={memberData}
        unit={unit}
        newProduct={newProduct}
        changeDate={changeDate}
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
            disabled={!unit || !isSubscriptionUnitEditable(unit)}
            onClick={() => setStep("change")}
          />
        );
      case "change":
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
              disabled={checking || !checkPassed}
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
              onClick={() => setStep("change")}
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
          <h5 className={"mb-0"}>Anteilsgröße ändern</h5>
          <TapirHelpButton text={HELP_TEXT} />
        </div>
      </Modal.Header>
      <Modal.Body>
        {step === "member" && renderMemberStep()}
        {step === "change" && renderChangeStep()}
        {step === "summary" && renderSummaryStep()}
      </Modal.Body>
      <Modal.Footer>{renderFooter()}</Modal.Footer>
    </Modal>
  );
};

export default AdminSubscriptionChangeModal;
