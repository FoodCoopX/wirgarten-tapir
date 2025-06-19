import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { PersonalData } from "../types/PersonalData.ts";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { Table } from "react-bootstrap";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import formatAddress from "../../utils/formatAddress.ts";
import { formatOpeningTimes } from "../utils/formatOpeningTimes.ts";
import { isProductTypeOrdered } from "../utils/isProductTypeOrdered.ts";
import { formatDateText } from "../../utils/formatDateText.ts";

interface BestellWizardSummaryProps {
  theme: TapirTheme;
  personalData: PersonalData;
  shoppingCart: ShoppingCart;
  selectedNumberOfCoopShares: number;
  productTypes: PublicProductType[];
  pickupLocation: PublicPickupLocation | undefined;
  priceOfAShare: number;
  firstDeliveryDatesByProductType: { [key: string]: Date };
  updateOrderFromSummary: (productType: PublicProductType) => void;
}

const BestellWizardSummary: React.FC<BestellWizardSummaryProps> = ({
  theme,
  personalData,
  shoppingCart,
  selectedNumberOfCoopShares,
  productTypes,
  pickupLocation,
  priceOfAShare,
  firstDeliveryDatesByProductType,
  updateOrderFromSummary,
}) => {
  function getProductIdsOfProductType(productType: PublicProductType) {
    return productType.products.map((product) => product.id);
  }

  function getProductById(productType: PublicProductType, productId: string) {
    return productType.products.find((product) => product.id === productId);
  }

  function buildProductTypeTable(productType: PublicProductType) {
    return (
      <Table bordered={true}>
        <tbody>
          <tr>
            <td>Erste Lieferung</td>
            <td>
              {formatDateText(firstDeliveryDatesByProductType[productType.id!])}
            </td>
          </tr>
          {Object.entries(shoppingCart)
            .filter(
              ([productId, quantity]) =>
                getProductIdsOfProductType(productType).includes(productId) &&
                quantity > 0,
            )
            .map(([productId, quantity]) => (
              <tr>
                <td>{getProductById(productType, productId)?.name}</td>
                <td>
                  {quantity} x{" "}
                  {formatCurrency(
                    getProductById(productType, productId)!.price,
                  )}
                </td>
              </tr>
            ))}
        </tbody>
      </Table>
    );
  }

  return (
    <>
      <BestellWizardCardTitle text={"Übersicht"} />
      <BestellWizardCardSubtitle
        text={"Deine Mitgliedschaft in der Genossenschaft"}
      />
      <Table bordered={true}>
        <tbody>
          <tr>
            <td>Deine Genossenschaftsanteile</td>
            <td>
              {selectedNumberOfCoopShares} * {formatCurrency(priceOfAShare)} ={" "}
              {formatCurrency(priceOfAShare * selectedNumberOfCoopShares)}
            </td>
          </tr>
          <tr>
            <td>Abbuchung</td>
            <td>TODO Abbuchung</td>
          </tr>
        </tbody>
      </Table>
      {productTypes.map((productType) => (
        <div className={"mt-2"} key={productType.id}>
          <BestellWizardCardSubtitle text={productType.name} />
          {isProductTypeOrdered(productType, shoppingCart) ? (
            buildProductTypeTable(productType)
          ) : (
            <span>Dieses Produkt ist nicht bestellt worden</span>
          )}
          <TapirButton
            icon={"edit"}
            text={"Bestellung anpassen"}
            variant={"outline-primary"}
            size={"sm"}
            onClick={() => updateOrderFromSummary(productType)}
          />
        </div>
      ))}
      {pickupLocation !== undefined && (
        <div className={"mt-2"}>
          <BestellWizardCardSubtitle text={"Deine Verteilstation"} />
          <Table bordered={true}>
            <tbody>
              <tr>
                <td>Adresse</td>
                <td>
                  {pickupLocation.name} <br />
                  {formatAddress(
                    pickupLocation.street,
                    pickupLocation.street2,
                    pickupLocation.postcode,
                    pickupLocation.city,
                  )}
                </td>
              </tr>
              <tr>
                <td>Öffnungszeiten</td>
                <td>{formatOpeningTimes(pickupLocation)}</td>
              </tr>
            </tbody>
          </Table>
        </div>
      )}
    </>
  );
};

export default BestellWizardSummary;
