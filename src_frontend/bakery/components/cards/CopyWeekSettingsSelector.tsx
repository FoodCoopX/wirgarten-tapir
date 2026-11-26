import React, { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { BakeryApi } from "../../../api-client";
import type {
  CopyWeekSettingsResponse,
  WeekSettingsSource,
} from "../../../api-client/models";
import TapirButton from "../../../components/TapirButton";
import { useApi } from "../../../hooks/useApi";
import { ToastData } from "../../../types/ToastData";
import { addToast } from "../../../utils/addToast";
import { handleRequestError } from "../../../utils/handleRequestError";
import { DAY_LABELS } from "../../utils/weekdays";

interface CopyWeekSettingsSelectorProps {
  year: number;
  week: number;
  csrfToken: string;
  disabled: boolean;
  onCopied: (
    result: CopyWeekSettingsResponse,
    target: { year: number; week: number },
  ) => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const sourceKey = (source: WeekSettingsSource) =>
  `${source.year}/${source.deliveryWeek}`;

const dayNames = (days: number[]) =>
  days.map((day) => DAY_LABELS[day] ?? `Tag ${day}`).join(", ");

export const CopyWeekSettingsSelector: React.FC<
  CopyWeekSettingsSelectorProps
> = ({ year, week, csrfToken, disabled, onCopied, setToastDatas }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [sources, setSources] = useState<WeekSettingsSource[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [copying, setCopying] = useState(false);
  const selectionRef = useRef(`${year}/${week}`);

  useEffect(() => {
    let cancelled = false;
    selectionRef.current = `${year}/${week}`;
    // The previous week's sources would offer later weeks as a template.
    setSources([]);
    setSelectedKey("");
    bakeryApi
      .bakeryApiCopyWeekSettingsRetrieve({ year, deliveryWeek: week })
      .then((response) => {
        if (!cancelled) setSources(response.sources);
      })
      .catch((error) => {
        if (cancelled) return;
        handleRequestError(
          error,
          "Fehler beim Laden der Vorwochen",
          setToastDatas,
        );
      });
    return () => {
      cancelled = true;
    };
  }, [year, week]);

  function notify(title: string) {
    addToast({ title, variant: "info", id: uuidv4() }, setToastDatas);
  }

  function confirmMessage(
    source: WeekSettingsSource,
    preview: CopyWeekSettingsResponse,
  ): string {
    const lines = [
      `Brote und Tageseinstellungen aus KW ${source.deliveryWeek}/${source.year} übernehmen?`,
      `In KW ${week}/${year} werden diese Tage vollständig ersetzt: ${dayNames(preview.copiedDays)}.`,
    ];
    if (preview.keptDays.length > 0) {
      lines.push(
        `Schon vorbei und unverändert: ${dayNames(preview.keptDays)}.`,
      );
    }
    if (preview.clearedChoices > 0) {
      lines.push(
        `${preview.clearedChoices} ${preview.clearedChoices === 1 ? "Brotwahl" : "Brotwahlen"} von Mitgliedern werden zurückgesetzt, weil ihr Brot an dem Tag nicht mehr gebacken wird. Sie werden nicht wiederhergestellt.`,
      );
    }
    return lines.join("\n\n");
  }

  function copySettings() {
    const source = sources.find((s) => sourceKey(s) === selectedKey);
    if (!source) return;

    const target = { year, week };
    const requestedFor = `${year}/${week}`;
    const request = {
      sourceYear: source.year,
      sourceWeek: source.deliveryWeek,
      targetYear: year,
      targetWeek: week,
    };

    // Ask with what the copy would do before doing it.
    setCopying(true);
    bakeryApi
      .bakeryApiCopyWeekSettingsCreate({
        copyWeekSettingsRequestRequest: { ...request, dryRun: true },
      })
      .then((preview) => {
        // Another week was selected meanwhile: don't copy into one that is no
        // longer shown.
        if (selectionRef.current !== requestedFor) {
          notify(
            `Nicht übernommen: Inzwischen ist eine andere Woche als KW ${week}/${year} ausgewählt.`,
          );
          return;
        }
        if (preview.copiedDays.length === 0) {
          notify(
            `Die Liefertage von KW ${week}/${year} sind schon vorbei, es wird nichts übernommen.`,
          );
          return;
        }
        if (!confirm(confirmMessage(source, preview))) return;

        return bakeryApi
          .bakeryApiCopyWeekSettingsCreate({
            copyWeekSettingsRequestRequest: request,
          })
          .then((result) => {
            setSelectedKey("");
            onCopied(result, target);
          });
      })
      .catch((error) => {
        handleRequestError(
          error,
          "Fehler beim Übernehmen der Einstellungen",
          setToastDatas,
        );
      })
      .finally(() => {
        setCopying(false);
      });
  }

  return (
    <div className="d-flex align-items-center gap-2">
      <label htmlFor="copy-week-settings-source" className="text-nowrap mb-0">
        Einstellungen übernehmen aus
      </label>
      <select
        id="copy-week-settings-source"
        className="form-select"
        value={selectedKey}
        onChange={(e) => setSelectedKey(e.target.value)}
        disabled={disabled || copying || sources.length === 0}
      >
        <option value="">
          {sources.length === 0
            ? "keine frühere Woche geplant"
            : "Woche wählen"}
        </option>
        {sources.map((source) => (
          <option key={sourceKey(source)} value={sourceKey(source)}>
            KW {source.deliveryWeek}/{source.year} ({source.breadCount}{" "}
            {source.breadCount === 1 ? "Brot" : "Brote"})
          </option>
        ))}
      </select>
      <TapirButton
        variant=""
        className="btn-bakery-brown text-nowrap"
        text="Übernehmen"
        icon="content_copy"
        onClick={copySettings}
        disabled={disabled || copying || selectedKey === ""}
        loading={copying}
        size="sm"
      />
    </div>
  );
};
