import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { Card, Form, Spinner } from "react-bootstrap";
import { useApi } from "../../hooks/useApi.ts";
import { CoreApi, type MailCategory } from "../../api-client";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import TapirButton from "../../components/TapirButton.tsx";

interface MemberMailCategoryModalProps {
  memberId: string;
  csrfToken: string;
}

const MemberMailCategoryCard: React.FC<MemberMailCategoryModalProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(CoreApi, csrfToken);
  const [categories, setCategories] = useState<MailCategory[]>([]);
  const [categoriesRegisteredTo, setCategoriesRegisteredTo] = useState<{
    [key: string]: boolean;
  }>({});
  const [dataLoading, setDataLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  function loadData() {
    setDataLoading(true);
    api
      .coreApiMemberMailCategoryDataRetrieve({ memberId: memberId })
      .then((data) => {
        setCategories(data.categories);
        setCategoriesRegisteredTo(data.categoriesRegisteredTo);
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Mail-Abos"),
      )
      .finally(() => setDataLoading(false));
  }

  function onSave() {
    setSaveLoading(true);

    api
      .coreApiMemberMailCategoryDataCreate({
        memberMailCategoryRequestRequest: {
          memberId: memberId,
          categoriesRegisteredTo: categoriesRegisteredTo,
        },
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Speichern der Mail-Abos"),
      )
      .finally(() => {
        setSaveLoading(false);
        loadData();
      });
  }

  return (
    <Card>
      <Card.Header>
        <h5 className={"mb-0"}>Mail-Abos</h5>
      </Card.Header>
      <Card.Body>
        {dataLoading ? (
          <Spinner />
        ) : (
          <Form>
            {categories.map((category) => (
              <Form.Group key={category.id} controlId={category.id}>
                <Form.Check
                  label={category.name}
                  checked={categoriesRegisteredTo[category.id!]}
                  onChange={(event) => {
                    categoriesRegisteredTo[category.id!] = event.target.checked;
                    setCategoriesRegisteredTo({ ...categoriesRegisteredTo });
                  }}
                />
              </Form.Group>
            ))}
          </Form>
        )}
      </Card.Body>
      <Card.Footer>
        <span className={"d-flex flex-row justify-content-end"}>
          <TapirButton
            variant={"primary"}
            text={"Speichern"}
            icon={"save"}
            onClick={onSave}
            loading={saveLoading}
          />
        </span>
      </Card.Footer>
    </Card>
  );
};

export default MemberMailCategoryCard;
