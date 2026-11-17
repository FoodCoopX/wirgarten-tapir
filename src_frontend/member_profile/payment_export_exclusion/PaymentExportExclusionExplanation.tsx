import React from "react";

const PaymentExportExclusionExplanation: React.FC = () => {
  return (
    <div className={"d-flex flex-column gap-2"}>
      <p className={"mb-0"}>
        In den eingetragenen Monaten werden die regelmäßigen Zahlungen des
        Mitglieds (Verträge, Solidarbeitrag, Vereinsbeitrag, Liefergebühren)
        nicht in die SEPA-Exporte übernommen, z. B. weil die Organisation dem
        Mitglied ein Darlehen über seinen Anteil zurückzahlt.
      </p>
      <p className={"mb-0"}>
        Die Zahlungen werden trotzdem erzeugt und als bezahlt markiert.
        Statistiken wie der Cashflow oder der Solidartopf bleiben daher
        unverändert. Genossenschaftsanteile werden weiterhin eingezogen.
      </p>
    </div>
  );
};

export default PaymentExportExclusionExplanation;
