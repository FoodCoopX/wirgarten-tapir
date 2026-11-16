import React from "react";

const PaymentExportExclusionExplanation: React.FC = () => {
  return (
    <div className={"d-flex flex-column gap-2"}>
      <p className={"mb-0"}>
        In den eingetragenen Monaten werden die regelmäßigen Zahlungen des
        Mitglieds (Verträge, Solidarbeitrag, Vereinsbeitrag, Liefergebühren)
        nicht in die SEPA-Exporte übernommen, z. B. weil das Mitglied einen
        Kredit über seinen Anteil zurückbezahlt.
      </p>
      <p className={"mb-0"}>
        Die Zahlungen werden trotzdem erzeugt und als bezahlt markiert.
        Genossenschaftsanteile werden weiterhin eingezogen.
      </p>
    </div>
  );
};

export default PaymentExportExclusionExplanation;
