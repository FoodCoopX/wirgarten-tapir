import React from "react";
import { Card } from "react-bootstrap";

import { formatCurrency } from "../../utils/formatCurrency.ts";

interface ProductCardProps {
  name: string;
  referenceValue?: string | null;
  imageUrl?: string | null;
  imageFilter?: string;
  selected?: boolean;
  onSelect?: () => void;
  children?: React.ReactNode;
}

const ProductCard: React.FC<ProductCardProps> = ({
  name,
  referenceValue,
  imageUrl,
  imageFilter,
  selected = false,
  onSelect,
  children,
}) => (
  <Card
    className={selected ? "border-dark" : ""}
    role={onSelect ? "button" : undefined}
    onClick={onSelect}
  >
    {imageUrl && (
      <Card.Img
        variant={"top"}
        src={imageUrl}
        style={{
          width: "auto",
          height: "auto",
          maxWidth: "40dvw",
          maxHeight: "30dvh",
          objectFit: "contain",
          display: "block",
          margin: "0 auto",
          filter: imageFilter,
        }}
      />
    )}
    <Card.Body>
      <Card.Title>{name}</Card.Title>
      {referenceValue && (
        <Card.Text className={"text-muted mb-0"}>
          Richtwert {formatCurrency(Number(referenceValue))}
        </Card.Text>
      )}
      {children}
    </Card.Body>
  </Card>
);

export default ProductCard;
