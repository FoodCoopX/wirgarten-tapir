import React, { useCallback, useEffect, useRef, useState } from "react";
import { PaymentsApi } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface MandateReferencePreviewProps {
  inputField: HTMLInputElement;
}

const MandateReferencePreview: React.FC<MandateReferencePreviewProps> = ({
  inputField,
}) => {
  const api = useApi(PaymentsApi, "unused");
  const [previews, setPreviews] = useState<Record<string, string>>();
  const [error, setError] = useState("");
  const abortControllerRef = useRef<AbortController>(undefined);

  const onPatternChanged = useCallback(() => {
    abortControllerRef.current?.abort();

    const localController = new AbortController();
    abortControllerRef.current = localController;

    api
      .paymentsApiMandateReferencePreviewRetrieve(
        { pattern: inputField.value },
        { signal: localController.signal },
      )
      .then((response) => {
        setPreviews(response.previews);
        setError(response.error);
      })
      .catch((error) => {
        if (error.cause?.name === "AbortError") return;

        handleRequestError(
          error,
          "Fehler beim Laden der Mandatsreferenz-Vorschau",
        );
      });
  }, [api, inputField]);

  useEffect(() => {
    inputField.addEventListener("input", onPatternChanged);
    inputField.addEventListener("change", onPatternChanged);

    return () => {
      inputField.removeEventListener("input", onPatternChanged);
      inputField.removeEventListener("change", onPatternChanged);
      abortControllerRef.current?.abort();
    };
  }, [inputField, onPatternChanged]);

  useEffect(() => {
    onPatternChanged();
  }, [onPatternChanged]);

  return (
    <div className={"form-text"}>
      {error ? (
        <span>Fehler: {error}</span>
      ) : (
        <span>
          Beispiele:
          <ul>
            {Object.entries(previews ?? {}).map(([member, reference]) => (
              <li key={member}>
                {member}: {reference}
              </li>
            ))}
          </ul>
        </span>
      )}
    </div>
  );
};

export default MandateReferencePreview;
