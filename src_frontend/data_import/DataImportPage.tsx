import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import {
  DataImportApi,
  ImportType,
  ImportTypesEnum,
  ReviewResponse,
  UploadResponse,
} from "../api-client";
import ConfirmModal from "../components/ConfirmModal";
import TapirToastContainer from "../components/TapirToastContainer";
import { useApi } from "../hooks/useApi";
import { ToastData } from "../types/ToastData";
import { addToast } from "../utils/addToast";
import { handleRequestError } from "../utils/handleRequestError";
import DataImportActivationCard from "./DataImportActivationCard";
import DataImportIntroCard from "./DataImportIntroCard";
import DataImportMappingCard from "./DataImportMappingCard";
import DataImportReviewCard from "./DataImportReviewCard";
import DataImportUploadCard from "./DataImportUploadCard";
import { effectivePickupMapping } from "./pickupLocationMapping";

export default function DataImportPage({ csrfToken }: { csrfToken: string }) {
  const api = useApi(DataImportApi, csrfToken);
  const [types, setTypes] = useState<ImportType[]>([]);
  const [selected, setSelected] = useState<string[]>(["members"]);
  const [file, setFile] = useState<File>();
  const [update, setUpdate] = useState(false);
  const [upload, setUpload] = useState<UploadResponse>();
  const [mapping, setMapping] = useState<Record<number, string>>({});
  const [defaults, setDefaults] = useState<Record<string, string>>({});
  const [options, setOptions] = useState({
    accountOwnerFromName: true,
    sepaConsentFromContractStart: true,
  });
  const [pickupMapping, setPickupMapping] = useState<Record<string, string>>(
    {},
  );
  const [createMissingPickupLocations, setCreateMissingPickupLocations] =
    useState(true);
  const [review, setReview] = useState<ReviewResponse>();
  const [selectedRows, setSelectedRows] = useState<number[]>([]);
  const [activation, setActivation] = useState(0);
  const [loading, setLoading] = useState(false);
  const [activationLoading, setActivationLoading] = useState(false);
  const [mappingErrors, setMappingErrors] = useState<string[]>([]);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [confirm, setConfirm] = useState<"apply" | "activation">();
  const error = (value: unknown, message: string) =>
    handleRequestError(value, message, setToastDatas);
  const loadActivation = () =>
    api
      .utilsDataImportActivationRetrieve()
      .then((result) => setActivation(result.membersWithoutLogin ?? 0))
      .catch((reason) =>
        error(reason, "Fehler beim Laden der Aktivierungsdaten"),
      );
  useEffect(() => {
    api
      .utilsDataImportTypesList()
      .then(setTypes)
      .catch((reason) => error(reason, "Fehler beim Laden der Importtypen"));
    loadActivation();
  }, []);
  const submitUpload = () => {
    if (!file) return;
    setLoading(true);
    api
      .utilsDataImportUploadCreate({
        file,
        importTypes: selected as ImportTypesEnum[],
        updateExisting: update,
      })
      .then((result) => {
        setUpload(result);
        setMapping(
          Object.fromEntries(
            result.columns.map((column) => [column.index, column.selectedKey]),
          ),
        );
        setPickupMapping({});
        setCreateMissingPickupLocations(true);
        setDefaults(
          Object.fromEntries(
            result.suggestedDefaults.map((item) => [item.key, item.value]),
          ),
        );
      })
      .catch((reason) => error(reason, "Fehler beim Hochladen der Datei"))
      .finally(() => setLoading(false));
  };
  const submitMapping = (updateOverride = update) => {
    if (!upload) return;
    setLoading(true);
    setMappingErrors([]);
    api
      .utilsDataImportMappingCreate({
        mappingRequestRequest: {
          token: upload.token,
          mapping: Object.entries(mapping).map(([columnIndex, key]) => ({
            columnIndex: Number(columnIndex),
            key,
          })),
          defaults: Object.entries(defaults).map(([key, value]) => ({
            key,
            value,
          })),
          options,
          updateExisting: updateOverride,
          pickupLocationMapping: effectivePickupMapping(
            upload,
            mapping,
            pickupMapping,
            createMissingPickupLocations,
          ),
        },
      })
      .then((result) => {
        setReview(result);
        setSelectedRows(
          result.rows
            .filter(
              (row) =>
                row.valid && (row.status === "new" || row.status === "changed"),
            )
            .map((row) => row.index),
        );
      })
      .catch(async (reason: unknown) => {
        if (reason instanceof Error && "response" in reason) {
          const response = (reason as { response?: Response }).response;
          const body = await response?.json().catch(() => undefined);
          if (body?.mapping_errors) {
            setMappingErrors(body.mapping_errors);
            return;
          }
        }
        error(reason, "Fehler bei der Zuordnung");
      })
      .finally(() => setLoading(false));
  };
  const editCell = (rowIndex: number, header: string, value: string) => {
    if (!upload) return Promise.resolve();
    setLoading(true);
    return api
      .utilsDataImportCellCreate({
        dataImportCellEditRequestRequest: {
          token: upload.token,
          rowIndex,
          header,
          value,
        },
      })
      .then((result) => {
        setReview(result);
        const selectable = (index: number) =>
          result.rows.some(
            (row) =>
              row.index === index &&
              row.valid &&
              (row.status === "new" || row.status === "changed"),
          );
        setSelectedRows((current) => {
          const kept = current.filter(selectable);
          return selectable(rowIndex) && !kept.includes(rowIndex)
            ? [...kept, rowIndex]
            : kept;
        });
      })
      .catch((reason) => error(reason, "Fehler beim Ändern der Zelle"))
      .finally(() => setLoading(false));
  };
  const apply = () => {
    if (!upload) return;
    setLoading(true);
    api
      .utilsDataImportApplyCreate({
        applyRequestRequest: { token: upload.token, rowIndices: selectedRows },
      })
      .then((result) => {
        addToast(
          {
            id: uuidv4(),
            variant: "success",
            title: "Datenübernahme",
            message: result.message,
          },
          setToastDatas,
        );
        reset();
        loadActivation();
      })
      .catch((reason) => error(reason, "Fehler bei der Übernahme"))
      .finally(() => {
        setLoading(false);
        setConfirm(undefined);
      });
  };
  const sendActivation = () => {
    setActivationLoading(true);
    api
      .utilsDataImportActivationCreate()
      .then((result) => {
        addToast(
          {
            id: uuidv4(),
            variant: "success",
            title: "Aktivierungsmails",
            message: `${result.sent ?? 0} Aktivierungsmails verschickt.`,
          },
          setToastDatas,
        );
        (result.errors ?? []).forEach((message) =>
          addToast(
            {
              id: uuidv4(),
              variant: "danger",
              title: "Aktivierungsmail nicht verschickt",
              message,
            },
            setToastDatas,
          ),
        );
        loadActivation();
      })
      .catch((reason) =>
        error(reason, "Fehler beim Verschicken der Aktivierungsmails"),
      )
      .finally(() => {
        setActivationLoading(false);
        setConfirm(undefined);
      });
  };
  const reset = () => {
    setUpload(undefined);
    setReview(undefined);
    setSelectedRows([]);
    setMappingErrors([]);
    setDefaults({});
    setPickupMapping({});
    setCreateMissingPickupLocations(true);
    setFile(undefined);
  };
  return (
    <>
      <div className="container py-3">
        <DataImportIntroCard types={types} />
        {!upload && (
          <DataImportUploadCard
            types={types}
            selected={selected}
            setSelected={setSelected}
            file={file}
            setFile={setFile}
            update={update}
            setUpdate={setUpdate}
            onSubmit={submitUpload}
            loading={loading}
          />
        )}
        {upload && !review && (
          <DataImportMappingCard
            upload={upload}
            mapping={mapping}
            setMapping={setMapping}
            defaults={defaults}
            options={options}
            setOptions={setOptions}
            setDefaults={setDefaults}
            pickupMapping={pickupMapping}
            setPickupMapping={setPickupMapping}
            createMissingPickupLocations={createMissingPickupLocations}
            setCreateMissingPickupLocations={setCreateMissingPickupLocations}
            errors={mappingErrors}
            onSubmit={submitMapping}
            loading={loading}
            onBack={reset}
          />
        )}
        {review && (
          <DataImportReviewCard
            review={review}
            selected={selectedRows}
            setSelected={setSelectedRows}
            onApply={() => setConfirm("apply")}
            onBack={() => setReview(undefined)}
            loading={loading}
            updateExisting={update}
            setUpdateExisting={setUpdate}
            onEdit={editCell}
            onRecheck={(value) => {
              setUpdate(value);
              submitMapping(value);
            }}
          />
        )}
        <DataImportActivationCard
          count={activation}
          onSend={() => setConfirm("activation")}
          loading={activationLoading}
        />
      </div>
      <ConfirmModal
        open={!!confirm}
        title={
          confirm === "apply"
            ? "Daten übernehmen?"
            : "Aktivierungsmails verschicken?"
        }
        message={
          confirm === "apply"
            ? "Die ausgewählten gültigen Zeilen werden jetzt übernommen."
            : `${activation} Aktivierungsmails werden verschickt.`
        }
        confirmButtonText={confirm === "apply" ? "Übernehmen" : "Verschicken"}
        confirmButtonVariant="primary"
        confirmButtonIcon={confirm === "apply" ? "check" : "mail"}
        onCancel={() => setConfirm(undefined)}
        onConfirm={confirm === "apply" ? apply : sendActivation}
        loading={loading || activationLoading}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
}
