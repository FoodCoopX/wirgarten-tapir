import TapirHelpButton from "../components/TapirHelpButton.tsx";

export const MODERATED_CHECKBOX_LABEL = (
  <span className={"d-flex gap-2"}>
    <span>E-Mails von Mitgliedern müssen von Admins freigegeben werden.</span>
    <TapirHelpButton
      text={
        <>
          <p>
            Wenn aktiviert, werden E-Mails von Empfänger:innen der Liste
            zurückgehalten und erst an alle weitergeleitet, nachdem Admins sie
            freigegeben haben.
          </p>
          <p className={"mb-0"}>
            Wenn deaktiviert, werden E-Mails von Empfänger:innen sofort an alle
            weitergeleitet.
          </p>
        </>
      }
      buttonSize={"sm"}
    />
  </span>
);
