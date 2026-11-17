import React from "react";
import { ADMIN_DOCS_BASE_URL } from "../../utils/ADMIN_DOCS_BASE_URL.ts";

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
      <p className={"mb-0"}>
        <a
          href={`${ADMIN_DOCS_BASE_URL}/payments/excluding_members_from_payment_exports/`}
          target={"_blank"}
          rel={"noreferrer"}
        >
          Dokumentation
        </a>
      </p>
    </div>
  );
};

export default PaymentExportExclusionExplanation;
