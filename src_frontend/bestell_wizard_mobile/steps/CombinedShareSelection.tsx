import { Form } from "react-bootstrap";
import { PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatPercentage } from "../../utils/formatPercentage.ts";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import { getProductById } from "../utils/getProductByIdGlobal.ts";
import { isProductOrdered } from "../utils/isProductOrdered.ts";

interface CombinedShareSelectionProps {
  productTypes: PublicProductType[];
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  productTypesInWaitingList: Set<PublicProductType>;
  chooseShare: (productType: PublicProductType, productId: string) => void;
  showError: boolean;
  stepActive: boolean;
}

export default function CombinedShareSelection({
  productTypes,
  settings,
  shoppingCart,
  productTypesInWaitingList,
  chooseShare,
  showError,
  stepActive,
}: CombinedShareSelectionProps) {
  return (
    <div className="d-flex flex-column gap-3" inert={!stepActive}>
      {productTypes.map((productType) => {
        const products = productType.products.filter(
          (product) => !product.hiddenInBestellWizard,
        );
        if (products.length === 0) {
          return null;
        }

        const pricedType =
          settings.productTypes.find((type) => type.id === productType.id) ??
          productType;
        const selectedProduct = products.find((product) =>
          isProductOrdered(product, shoppingCart),
        );
        const selectedPrice = selectedProduct
          ? (getProductById(pricedType, selectedProduct.id!)?.price ??
            selectedProduct.price)
          : undefined;
        const pricePeriod = productType.pricePerDelivery
          ? "Lieferung"
          : "Monat";
        const required = productType.mustBeSubscribedTo;
        const description =
          productType.descriptionBestellwizardLong ||
          productType.descriptionBestellwizardShort;
        const accordions = productType.accordions ?? [];
        return (
          <Form.Group
            key={productType.id}
            controlId={`share-${productType.id}`}
          >
            <Form.Label>
              {productType.name}
              {!required && " (optional)"}
            </Form.Label>
            <Form.Select
              value={selectedProduct?.id ?? ""}
              onChange={(event) => chooseShare(productType, event.target.value)}
              disabled={!stepActive}
              required={required}
              isInvalid={showError && required && !selectedProduct}
            >
              <option value="" disabled={required}>
                {required ? "Bitte auswählen" : "Kein Anteil"}
              </option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name} ·{" "}
                  {formatCurrency(
                    getProductById(pricedType, product.id!)?.price ??
                      product.price,
                  )}{" "}
                  / {pricePeriod}
                </option>
              ))}
            </Form.Select>
            <Form.Control.Feedback type="invalid">
              Bitte wähle einen Anteil aus.
            </Form.Control.Feedback>
            {selectedProduct &&
              [...productTypesInWaitingList].some(
                (type) => type.id === productType.id,
              ) && (
                <Form.Text className="text-danger">
                  Dieser Anteil kommt auf die Warteliste.
                </Form.Text>
              )}
            {selectedProduct?.urlOfImageInBestellwizard && (
              <img
                className="img-fluid d-block mt-2"
                src={selectedProduct.urlOfImageInBestellwizard}
                alt={productType.name + " " + selectedProduct.name}
                style={{ maxHeight: "12rem" }}
              />
            )}
            {selectedPrice !== undefined && (
              <Form.Text as="div">
                {settings.strings.step4bBasePriceLabel}:{" "}
                {formatCurrency(selectedPrice)} pro {pricePeriod}
                {productType.taxRate > 0 &&
                  " inkl. MwSt " + formatPercentage(productType.taxRate)}
                .
              </Form.Text>
            )}
            {selectedProduct?.descriptionInBestellwizard && (
              <Form.Text
                as="div"
                dangerouslySetInnerHTML={getHtmlDescription(
                  selectedProduct.descriptionInBestellwizard,
                )}
              />
            )}
            {(description || accordions.length > 0) && (
              <details className="small mt-1">
                <summary>Mehr zu {productType.name}</summary>
                {description && (
                  <div
                    dangerouslySetInnerHTML={getHtmlDescription(description)}
                  />
                )}
                {accordions.map((accordion) => (
                  <details key={accordion.order}>
                    <summary>{accordion.title}</summary>
                    <div
                      dangerouslySetInnerHTML={getHtmlDescription(
                        accordion.description,
                      )}
                    />
                  </details>
                ))}
              </details>
            )}
          </Form.Group>
        );
      })}
      {showError &&
        !productTypes.some((type) => type.mustBeSubscribedTo) &&
        !Object.values(shoppingCart).some((quantity) => quantity > 0) && (
          <div className="text-danger">Wähle mindestens einen Anteil aus.</div>
        )}
    </div>
  );
}
