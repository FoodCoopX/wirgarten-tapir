import React from "react";
import type {
  BreadList,
  PickupLocationDeliveryDay,
} from "../../../api-client/models";

export interface AllocationData {
  [pickupLocationId: string]: {
    [breadId: string]: number | null;
  };
}

interface AllocationTableProps {
  activeBreads: BreadList[];
  pickupLocations: PickupLocationDeliveryDay[];
  allocations: AllocationData;
  onCellChange: (
    pickupLocationId: string,
    breadId: string,
    value: number | null,
  ) => void;
}

export const AllocationTable: React.FC<AllocationTableProps> = ({
  activeBreads,
  pickupLocations,
  allocations,
  onCellChange,
}) => {
  const sumValues = (values: (number | null)[]): number => {
    return values.reduce<number>((sum, val) => sum + (val ?? 0), 0);
  };

  const getRowSum = (locationId: string): number => {
    return sumValues(
      activeBreads.map((bread) => allocations[locationId]?.[bread.id!] ?? null),
    );
  };

  const getColSum = (breadId: string): number => {
    return sumValues(
      pickupLocations.map(
        (location) => allocations[location.id]?.[breadId] ?? null,
      ),
    );
  };

  const getTotalSum = (): number => {
    return pickupLocations.reduce((total, location) => {
      return (
        total +
        sumValues(
          activeBreads.map(
            (bread) => allocations[location.id]?.[bread.id!] ?? null,
          ),
        )
      );
    }, 0);
  };

  const formatSum = (sum: number): string => {
    if (sum === 0) return "-";
    return String(sum);
  };

  return (
    <div className="card">
      <div className="card-body p-0">
        <div className="table-responsive">
          <table className="table table-bordered table-hover mb-0">
            <thead
              className="table-header-bakery"
              style={{ position: "sticky", top: 0, zIndex: 10 }}
            >
              <tr>
                <th style={{ minWidth: "150px" }}>Abholort</th>
                {activeBreads.map((bread) => (
                  <th
                    key={bread.id}
                    className="text-center"
                    style={{ minWidth: "120px" }}
                  >
                    {bread.name}
                  </th>
                ))}
                <th
                  className="text-center bg-bakery-cream"
                  style={{ minWidth: "80px" }}
                >
                  Σ
                </th>
              </tr>
            </thead>
            <tbody>
              {pickupLocations.map((location) => {
                const rowSum = getRowSum(location.id);

                return (
                  <tr key={location.id}>
                    <td className="fw-bold align-middle">{location.name}</td>
                    {activeBreads.map((bread) => (
                      <td key={bread.id} className="p-1">
                        {/* A capacity is a non-negative whole number and the
                            column carries CHECK (capacity >= 0). Note that a
                            browser reports unparseable input ("12-", "1e-") as
                            an EMPTY value with validity.badInput set, so
                            mapping empty to null would delete the capacity the
                            user had already stored on a mere typo. */}
                        <input
                          type="number"
                          min={0}
                          step={1}
                          className="form-control form-control-sm text-center"
                          value={allocations[location.id]?.[bread.id!] ?? ""}
                          onChange={(e) => {
                            const raw = e.target.value;
                            if (raw === "") {
                              // Genuinely cleared, not mistyped.
                              if (e.target.validity.badInput) return;
                              onCellChange(location.id, bread.id!, null);
                              return;
                            }
                            const parsed = Number(raw);
                            if (!Number.isFinite(parsed)) return;
                            onCellChange(
                              location.id,
                              bread.id!,
                              Math.max(0, Math.round(parsed)),
                            );
                          }}
                          placeholder="-"
                          style={{
                            minWidth: "60px",
                            fontSize: "14px",
                          }}
                        />
                      </td>
                    ))}
                    <td
                      className="text-center align-middle fw-bold bg-bakery-cream"
                      style={{ fontSize: "14px" }}
                    >
                      {formatSum(rowSum)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="bg-bakery-cream">
                <td className="fw-bold bg-bakery-cream">Σ Gesamt</td>
                {activeBreads.map((bread) => (
                  <td
                    key={bread.id}
                    className="text-center fw-bold align-middle bg-bakery-cream"
                    style={{ fontSize: "14px" }}
                  >
                    {formatSum(getColSum(bread.id!))}
                  </td>
                ))}
                <td
                  className="text-center fw-bold align-middle bg-bakery-primary text-white"
                  style={{ fontSize: "14px" }}
                >
                  {formatSum(getTotalSum())}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
};
