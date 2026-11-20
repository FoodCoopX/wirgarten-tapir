import React from "react";
import { Card, Collapse } from "react-bootstrap";

interface CollapsibleCardProps {
  title: React.ReactNode;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const CollapsibleCard: React.FC<CollapsibleCardProps> = ({
  title,
  open,
  onToggle,
  children,
}) => (
  <Card className="mb-4">
    <Card.Header>
      <button
        type="button"
        className="btn btn-link p-0 text-decoration-none text-start w-100 d-flex align-items-center gap-1"
        onClick={onToggle}
        aria-expanded={open}
      >
        <span className="material-icons">
          {open ? "expand_less" : "expand_more"}
        </span>
        <span className="h5 mb-0">{title}</span>
      </button>
    </Card.Header>
    <Collapse in={open} mountOnEnter unmountOnExit>
      <div>
        <Card.Body>{children}</Card.Body>
      </div>
    </Collapse>
  </Card>
);

export default CollapsibleCard;
