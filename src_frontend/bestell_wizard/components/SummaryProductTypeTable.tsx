import React from "react";
import { Table } from "react-bootstrap";
import { formatDateText } from "../../utils/formatDateText.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";

interface SummaryProductTypeTableProps {
  waitingListModeEnabled: boolean;
  firstDeliveryDatesByProductType: { [key: string]: Date };
  productType: PublicProductType;
  shoppingCart: ShoppingCart;
}

const SummaryProductTypeTable: React.FC<SummaryProductTypeTableProps> = ({
  waitingListModeEnabled,
  firstDeliveryDatesByProductType,
  productType,
  shoppingCart,
}) => {
  function getProductIdsOfProductType(productType: PublicProductType) {
    return productType.products.map((product) => product.id);
  }

  function getProductById(productType: PublicProductType, productId: string) {
    return productType.products.find((product) => product.id === productId);
  }

  return (
    <Table bordered={true}>
      <tbody>
        {!waitingListModeEnabled && (
          <tr>
            <td>Erste Lieferung</td>
            <td>
              {formatDateText(firstDeliveryDatesByProductType[productType.id!])}
            </td>
          </tr>
        )}
        {Object.entries(shoppingCart)
          .filter(
            ([productId, quantity]) =>
              getProductIdsOfProductType(productType).includes(productId) &&
              quantity > 0,
          )
          .map(([productId, quantity]) => (
            <tr key={productId}>
              <td>{getProductById(productType, productId)?.name}</td>
              <td>
                {quantity} x{" "}
                {formatCurrency(getProductById(productType, productId)!.price)}
              </td>
            </tr>
          ))}
      </tbody>
    </Table>
  );
};

export default SummaryProductTypeTable;
