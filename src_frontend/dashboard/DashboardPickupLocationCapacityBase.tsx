import React from "react";
import { Card } from "react-bootstrap";

interface GrowingPeriodBaseProps {}

const DashboardPickupLocationCapacityBase: React.FC<
  GrowingPeriodBaseProps
> = ({}) => {
  return (
    <Card>
      <Card.Header>Coucou</Card.Header>
      <Card.Body>Ouech</Card.Body>
    </Card>
  );
};

export default DashboardPickupLocationCapacityBase;
