import React from "react";
import TapirHelpButton from "../components/TapirHelpButton.tsx";

const MemberSearchHelpButton: React.FC = () => {
  return (
    <TapirHelpButton
      title={"Suche"}
      buttonSize={"sm"}
      text={
        <>
          <p>
            <strong>Durchsucht werden:</strong> Vorname, Nachname,
            E-Mail-Adresse und Mitgliedsnummer (auch mit führenden Nullen oder
            Präfix, z. B. „17“, „0017“ oder „BT0017“).
          </p>
          <p>
            <strong>Teilwörter</strong> genügen, Groß-/Kleinschreibung ist egal:
            „mus“ findet „Mustermann“.
          </p>
          <p>
            <strong>Mehrere Wörter:</strong> Es werden nur Mitglieder angezeigt,
            auf die <em>alle</em> Wörter zutreffen – die Reihenfolge ist egal.
            „Anna Muster“ und „Muster Anna“ finden dasselbe; „Anna gmx“ findet
            alle Annas mit einer GMX-Adresse.
          </p>
          <p className={"mb-0"}>
            Umlaute müssen exakt eingegeben werden („Müller“, nicht „Muller“).
            Telefonnummer, Adresse und Abholort werden nicht durchsucht – für
            den Abholort gibt es einen eigenen Filter.
          </p>
        </>
      }
    />
  );
};

export default MemberSearchHelpButton;
