import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { PersonalData } from "../types/PersonalData.ts";
import BestellWizardCardTitle from "../BestellWizardCardTitle.tsx";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import BestellWizardCardSubtitle from "../BestellWizardCardSubtitle.tsx";
import { Table } from "react-bootstrap";
import { PublicProductType } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";

interface BestellWizardSummaryProps {
  theme: TapirTheme;
  personalData: PersonalData;
  shoppingCart: ShoppingCart;
  selectedNumberOfCoopShares: number;
  productTypes: PublicProductType[];
}

const BestellWizardSummary: React.FC<BestellWizardSummaryProps> = ({
  theme,
  personalData,
  shoppingCart,
  selectedNumberOfCoopShares,
  productTypes,
}) => {
  function isProductTypeOrdered(productType: PublicProductType) {
    for (const [productId, quantity] of Object.entries(shoppingCart)) {
      if (
        productType.products.map((product) => product.id).includes(productId) &&
        quantity > 0
      ) {
        return true;
      }
    }
    return false;
  }

  function buildProductTypeTable() {
    return (
      <Table bordered={true}>
        <tbody>
          <tr>
            <td>Erste Lieferung</td>
            <td>TODO</td>
          </tr>
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
            <td>{selectedNumberOfCoopShares} * TODO PRICE</td>
          </tr>
          <tr>
            <td>Abbuchung</td>
            <td>TODO Abbuchung</td>
          </tr>
        </tbody>
      </Table>
      {productTypes.map((productType) => (
        <div className={"mt-2"}>
          <BestellWizardCardSubtitle text={productType.name} />
          {isProductTypeOrdered(productType) ? (
            buildProductTypeTable()
          ) : (
            <span>Dieses Produkt ist nicht bestellt worden</span>
          )}
          <TapirButton
            icon={"edit"}
            text={"Bestellung anpassen"}
            variant={"outline-primary"}
            size={"sm"}
          />
        </div>
      ))}
    </>
  );
};

export default BestellWizardSummary;
