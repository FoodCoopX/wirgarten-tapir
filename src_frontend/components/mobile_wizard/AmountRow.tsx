import React from "react";

import { formatAmountNumber } from "../../utils/formatAmountNumber.ts";

interface AmountRowProps {
  label: string;
  amount: number | null;
  unit: string;
  hint?: string;
  muted?: boolean;
  strong?: boolean;
  labelStrong?: boolean;
}

const AmountRow: React.FC<AmountRowProps> = ({
  label,
  amount,
  unit,
  hint,
  muted = true,
  strong = false,
  labelStrong = false,
}) => {
  const display =
    amount === null ? "–" : `${formatAmountNumber(amount)} ${unit}`;

  return (
    <div className={"d-flex justify-content-between gap-3"}>
      <span className={muted ? "text-muted" : ""}>
        {labelStrong ? <strong>{label}</strong> : label}
        {hint && <span className={"d-block small text-muted"}>{hint}</span>}
      </span>
      <span className={"text-nowrap"}>
        {strong ? <strong>{display}</strong> : display}
      </span>
    </div>
  );
};

export default AmountRow;
