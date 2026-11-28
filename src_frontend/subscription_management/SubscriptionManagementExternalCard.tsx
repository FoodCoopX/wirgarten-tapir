import React, { useState } from "react";
import { Card, Form } from "react-bootstrap";
import { SubscriptionManagementExternalPart } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import MailCategoryCheckboxes from "../member_profile/mail_category/MailCategoryCheckboxes.tsx";

interface SubscriptionManagementExternalCardProps {
  external: SubscriptionManagementExternalPart;
  saving: boolean;
  onSave: (
    firstName: string,
    categoriesRegisteredTo: { [key: string]: boolean },
  ) => void;
  onRemove: () => void;
}

const SubscriptionManagementExternalCard: React.FC<
  SubscriptionManagementExternalCardProps
> = ({ external, saving, onSave, onRemove }) => {
  const [firstName, setFirstName] = useState(external.firstName);
  const [categoriesRegisteredTo, setCategoriesRegisteredTo] = useState(
    external.categoriesRegisteredTo,
  );

  return (
    <Card>
      <Card.Header>
        <h5 className={"mb-0"}>Newsletter</h5>
      </Card.Header>
      <Card.Body className={"d-flex flex-column gap-2"}>
        <Form.Group controlId={"external_first_name"}>
          <Form.Label>Vorname</Form.Label>
          <Form.Control
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
          />
        </Form.Group>
        <MailCategoryCheckboxes
          categories={external.categories}
          categoriesRegisteredTo={categoriesRegisteredTo}
          setCategoriesRegisteredTo={setCategoriesRegisteredTo}
          alwaysOnIsLocked={false}
        />
      </Card.Body>
      <Card.Footer>
        <span className={"d-flex flex-wrap justify-content-between gap-2"}>
          <TapirButton
            variant={"outline-danger"}
            icon={"unsubscribe"}
            text={"Abmelden"}
            onClick={onRemove}
          />
          <TapirButton
            variant={"primary"}
            icon={"save"}
            text={"Speichern"}
            onClick={() => onSave(firstName, categoriesRegisteredTo)}
            loading={saving}
          />
        </span>
      </Card.Footer>
    </Card>
  );
};

export default SubscriptionManagementExternalCard;
