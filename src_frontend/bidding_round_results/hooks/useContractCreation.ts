import type { Dispatch, SetStateAction } from "react";
import { useState } from "react";

import type { BiddingRoundsApi } from "../../api-client/apis/BiddingRoundsApi.ts";
import type { CreateContractsError } from "../../api-client/models/CreateContractsError.ts";
import type { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { interpolate } from "../../utils/interpolate.ts";

interface UseContractCreationParams {
  api: BiddingRoundsApi;
  roundId: string;
  selectedBidIds: string[];
  selectedAutoRenewedMemberIds: string[];
  createAutoRenewed: boolean;
  setCreateAutoRenewed: (enabled: boolean) => void;
  setResultMessage: (message: string | null) => void;
  setErrorReport: (errors: CreateContractsError[]) => void;
  setToastDatas: Dispatch<SetStateAction<ToastData[]>>;
  loadResults: (autoJump?: boolean) => void;
}

export function useContractCreation({
  api,
  roundId,
  selectedBidIds,
  selectedAutoRenewedMemberIds,
  createAutoRenewed,
  setCreateAutoRenewed,
  setResultMessage,
  setErrorReport,
  setToastDatas,
  loadResults,
}: UseContractCreationParams) {
  const [showContractsModal, setShowContractsModal] = useState(false);
  const [checkLoading, setCheckLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [checkMessage, setCheckMessage] = useState<string | null>(null);
  const [checkErrors, setCheckErrors] = useState<CreateContractsError[]>([]);
  const [standardPriceSaving, setStandardPriceSaving] = useState(false);

  const runCheckContracts = async () => {
    setCheckLoading(true);
    setCheckMessage(null);
    try {
      const response = await api.biddingRoundsApiCheckContractsCreate({
        roundId,
        checkContractsRequest: { bidIds: selectedBidIds },
      });
      const errors = response.errors ?? [];
      setCheckErrors(errors);
      setCheckMessage(
        errors.length === 0
          ? "Aus allen ausgewählten Geboten können Verträge erzeugt werden."
          : interpolate(
              "Aus {count} Geboten können keine Verträge erzeugt werden.",
              { count: errors.length },
            ),
      );
    } catch (e) {
      handleRequestError(
        e,
        "Die Verträge konnten nicht geprüft werden.",
        setToastDatas,
      );
    } finally {
      setCheckLoading(false);
    }
  };

  const createContracts = async () => {
    setCreateLoading(true);
    try {
      const response = await api.biddingRoundsApiCreateContractsCreate({
        roundId,
        createContractsRequest: {
          bidIds: selectedBidIds,
          autoRenewedMemberIds: selectedAutoRenewedMemberIds,
          createAutoRenewedContracts: createAutoRenewed,
        },
      });
      const errors = response.errors ?? [];
      setErrorReport(errors);
      setResultMessage(
        errors.length === 0
          ? "Verträge erzeugt."
          : interpolate("Verträge erzeugt mit {count} Fehlern.", {
              count: errors.length,
            }),
      );
      setShowContractsModal(false);
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Verträge konnten nicht erzeugt werden.",
        setToastDatas,
      );
    } finally {
      setCreateLoading(false);
    }
  };

  const openContractsModal = () => {
    setCreateAutoRenewed(selectedAutoRenewedMemberIds.length > 0);
    setCheckMessage(null);
    setCheckErrors([]);
    setShowContractsModal(true);
    runCheckContracts();
  };

  const alignStandardPrices = async () => {
    setStandardPriceSaving(true);
    try {
      const response = await api.biddingRoundsApiAlignStandardPricesCreate({
        roundId,
      });
      const results = response.results ?? [];
      setResultMessage(
        results.length === 0
          ? "Keine Standardpreise zum Angleichen gefunden."
          : interpolate("Standardpreise angeglichen ({count} Produkte).", {
              count: results.length,
            }),
      );
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Die Standardpreise konnten nicht angeglichen werden.",
        setToastDatas,
      );
    } finally {
      setStandardPriceSaving(false);
    }
  };

  return {
    showContractsModal,
    setShowContractsModal,
    checkLoading,
    createLoading,
    checkMessage,
    checkErrors,
    runCheckContracts,
    createContracts,
    openContractsModal,
    standardPriceSaving,
    alignStandardPrices,
  };
}
