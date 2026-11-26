import { Variant } from "react-bootstrap/types";

enum ElementType {
  Filter,
  Operator,
  OpenBracket,
  CloseBracket,
  Not,
}

type FilterElement = {
  value: string;
  elementType: ElementType;
};

const FILTER_ELEMENT_COLORS: { [key in ElementType]: Variant } = {
  [ElementType.Filter]: "dark",
  [ElementType.Operator]: "primary",
  [ElementType.OpenBracket]: "info",
  [ElementType.CloseBracket]: "info",
  [ElementType.Not]: "warning",
};

const guessElementType = (value: string): ElementType => {
  switch (value) {
    case "AND":
    case "OR":
      return ElementType.Operator;
    case "(":
      return ElementType.OpenBracket;
    case ")":
      return ElementType.CloseBracket;
    case "NOT":
      return ElementType.Not;
    default:
      return ElementType.Filter;
  }
};

export {
  ElementType,
  FILTER_ELEMENT_COLORS,
  guessElementType,
  type FilterElement,
};
