import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { Form, Modal, Spinner } from "react-bootstrap";
import { useApi } from "../../hooks/useApi.ts";
import { CoreApi, type MailCategory } from "../../api-client";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import TapirButton from "../../components/TapirButton.tsx";

interface MemberMailCategoryModalProps {
  memberId: string;
  csrfToken: string;
  open: boolean;
  onClose: () => void;
}

const MemberMailCategoryModal: React.FC<MemberMailCategoryModalProps> = ({
  memberId,
  csrfToken,
  open,
  onClose,
}) => {
  const api = useApi(CoreApi, csrfToken);
  const [categories, setCategories] = useState<MailCategory[]>([]);
  const [categoriesRegisteredTo, setCategoriesRegisteredTo] = useState<{
    [key: string]: boolean;
  }>({});
  const [dataLoading, setDataLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }

    setDataLoading(true);
    api
      .coreApiMemberMailCategoryDataRetrieve({ memberId: memberId })
      .then((data) => {
        setCategories(data.categories);
        setCategoriesRegisteredTo(data.categoriesRegisteredTo);
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Newsletter-Daten"),
      )
      .finally(() => setDataLoading(false));
  }, [open]);

  function onSave() {
    setSaveLoading(true);

    api
      .coreApiMemberMailCategoryDataCreate({
        memberMailCategoryRequestRequest: {
          memberId: memberId,
          categoriesRegisteredTo: categoriesRegisteredTo,
        },
      })
      .then(() => {
        onClose();
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Speichern der Newsletter-Daten"),
      )
      .finally(() => setSaveLoading(false));
  }

  return (
    <Modal show={open} onHide={onClose} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Newsletter-Abo verwalten</h5>
      </Modal.Header>
      <Modal.Body>
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
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          text={"Speichern"}
          icon={"save"}
          onClick={onSave}
          loading={saveLoading}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default MemberMailCategoryModal;
