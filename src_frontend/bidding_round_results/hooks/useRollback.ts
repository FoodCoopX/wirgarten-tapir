import type { Dispatch, SetStateAction } from "react";
import { useState } from "react";

import { ResponseError } from "../../api-client";
import type { BiddingRoundsApi } from "../../api-client/apis/BiddingRoundsApi.ts";
import type { RollbackResult } from "../../api-client/models/RollbackResult.ts";
import type { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { interpolate } from "../../utils/interpolate.ts";
import type { RollbackConflict, RollbackTarget } from "../types.ts";

interface RollbackErrorBody {
  code?: string;
  error?: string;
  conflicts?: RollbackConflict[];
}

interface UseRollbackArgs {
  api: BiddingRoundsApi;
  roundId: string;
  reload: () => void;
  setResultMessage: (message: string) => void;
  setToastDatas: Dispatch<SetStateAction<ToastData[]>>;
}

export function useRollback({
  api,
  roundId,
  reload,
  setResultMessage,
  setToastDatas,
}: UseRollbackArgs) {
  const [target, setTarget] = useState<RollbackTarget | null>(null);
  const [reason, setReason] = useState("");
  const [force, setForce] = useState(false);
  const [conflicts, setConflicts] = useState<RollbackConflict[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const openRollbackModal = (
    memberIds: string[] | null,
    memberNames: string[],
  ) => {
    setTarget({ memberIds, memberNames });
    setReason("");
    setForce(false);
    setConflicts([]);
    setError(null);
  };

  const closeRollbackModal = () => {
    if (!loading) {
      setTarget(null);
    }
  };

  const readErrorBody = async (
    requestError: unknown,
  ): Promise<RollbackErrorBody | null> => {
    if (requestError instanceof ResponseError) {
      return (await requestError.response
        .clone()
        .json()
        .catch(() => null)) as RollbackErrorBody | null;
    }
    return null;
  };

  const runRollback = async () => {
    if (!target) {
      return;
    }
    if (force && !reason.trim()) {
      setError("Bitte für die erzwungene Rücknahme eine Begründung angeben.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await api.biddingRoundsApiRollbackMembersCreate({
        roundId,
        rollbackMembersRequest: {
          all: target.memberIds === null,
          memberIds: target.memberIds ?? undefined,
          force,
          reason,
        },
      });
      const results: RollbackResult[] = response.results ?? [];
      const reverted = results.filter((result) => result.state === "reverted");
      setResultMessage(
        interpolate(
          "Verträge zurückgenommen: {subscriptions} gelöscht, {contributions} Beiträge wiederhergestellt.",
          {
            subscriptions: reverted.reduce(
              (sum, result) => sum + result.subscriptionsDeleted,
              0,
            ),
            contributions: reverted.reduce(
              (sum, result) => sum + result.contributionsRestored,
              0,
            ),
          },
        ),
      );
      setTarget(null);
      reload();
    } catch (requestError) {
      const body = await readErrorBody(requestError);
      if (body?.code === "diverged") {
        setConflicts(body.conflicts ?? []);
        setForce(false);
        setError(body.error ?? "Der Rollback steht im Konflikt.");
      } else if (body?.code === "cross_round") {
        setConflicts(body.conflicts ?? []);
        setError(body.error ?? "Eine andere Runde hängt an diesen Verträgen.");
      } else if (body?.error) {
        setError(body.error);
      } else {
        handleRequestError(
          requestError,
          "Die Verträge konnten nicht zurückgenommen werden.",
          setToastDatas,
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return {
    target,
    reason,
    setReason,
    force,
    setForce,
    conflicts,
    error,
    loading,
    openRollbackModal,
    closeRollbackModal,
    runRollback,
  };
}
