import React, { useState } from "react";
import { Card } from "react-bootstrap";
import { SubscriptionManagementExtraPart } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import MailCategoryCheckboxes from "../member_profile/mail_category/MailCategoryCheckboxes.tsx";

interface SubscriptionManagementExtraCardProps {
  extra: SubscriptionManagementExtraPart;
  saving: boolean;
  onSave: (categoriesRegisteredTo: { [key: string]: boolean }) => void;
  onRemove: () => void;
}

const SubscriptionManagementExtraCard: React.FC<
  SubscriptionManagementExtraCardProps
> = ({ extra, saving, onSave, onRemove }) => {
  const [categoriesRegisteredTo, setCategoriesRegisteredTo] = useState(
    extra.categoriesRegisteredTo,
  );

  return (
    <Card>
      <Card.Header>
        <h5 className={"mb-0"}>
          Zusätzliche Adresse von {extra.memberFirstName}
        </h5>
      </Card.Header>
      <Card.Body>
        <p>
          {extra.receivesDirectMails
            ? `Diese Adresse bekommt eine Kopie der persönlichen Mails an ${extra.memberFirstName}, und dazu die Mails der folgenden Kategorien.`
            : "Diese Adresse bekommt die Mails der folgenden Kategorien."}
        </p>
        <MailCategoryCheckboxes
          categories={extra.categories}
          categoriesRegisteredTo={categoriesRegisteredTo}
          setCategoriesRegisteredTo={setCategoriesRegisteredTo}
          alwaysOnIsLocked={false}
        />
      </Card.Body>
      <Card.Footer>
        <span className={"d-flex flex-wrap justify-content-between gap-2"}>
          <TapirButton
            variant={"outline-danger"}
            icon={"person_remove"}
            text={`Verbindung zu ${extra.memberFirstName} trennen`}
            onClick={onRemove}
          />
          <TapirButton
            variant={"primary"}
            icon={"save"}
            text={"Speichern"}
            onClick={() => onSave(categoriesRegisteredTo)}
            loading={saving}
          />
        </span>
      </Card.Footer>
    </Card>
  );
};

export default SubscriptionManagementExtraCard;
