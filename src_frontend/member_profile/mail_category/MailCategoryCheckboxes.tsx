import React from "react";
import { Form } from "react-bootstrap";
import { ModeEnum } from "../../api-client";

interface MailCategoryCheckboxesProps {
  categories: { id?: string; name: string; mode: ModeEnum }[];
  categoriesRegisteredTo: { [key: string]: boolean };
  setCategoriesRegisteredTo: (categoriesRegisteredTo: {
    [key: string]: boolean;
  }) => void;
  alwaysOnIsLocked: boolean;
}

const MailCategoryCheckboxes: React.FC<MailCategoryCheckboxesProps> = ({
  categories,
  categoriesRegisteredTo,
  setCategoriesRegisteredTo,
  alwaysOnIsLocked,
}) => {
  if (categories.length === 0) {
    return <p className={"mb-0"}>Keine Mail-Kategorie verfügbar</p>;
  }

  return (
    <Form>
      {categories.map((category) => (
        <Form.Group key={category.id} controlId={category.id}>
          <Form.Check
            label={category.name}
            checked={categoriesRegisteredTo[category.id!]}
            onChange={(event) =>
              setCategoriesRegisteredTo({
                ...categoriesRegisteredTo,
                [category.id!]: event.target.checked,
              })
            }
            disabled={alwaysOnIsLocked && category.mode === ModeEnum.AlwaysOn}
          />
        </Form.Group>
      ))}
    </Form>
  );
};

export default MailCategoryCheckboxes;
