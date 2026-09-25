import React, { useEffect, useState } from "react";
import { Card, Spinner } from "react-bootstrap";
import { BakeryApi } from "../api-client";
import { PreferredBreadStatisticsCard } from "../bakery/components/cards/PreferredBreadStatisticsCard";
import {
  currentIsoWeek,
  currentIsoYear,
  DAY_LABELS,
} from "../bakery/utils/weekdays";
import { useApi } from "../hooks/useApi";

const DashboardPreferredBreadStats: React.FC = () => {
  const bakeryApi = useApi(BakeryApi, "no_token");
  const [deliveryDays, setDeliveryDays] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  const year = currentIsoYear();
  const week = currentIsoWeek();

  useEffect(() => {
    bakeryApi
      .bakeryApiDeliveryDaysRetrieve()
      .then((data) => setDeliveryDays(data.days))
      .catch((err) => console.error("Failed to load delivery days:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Card>
        <Card.Header>
          <h5 className="mb-0">Lieblingsbrote</h5>
        </Card.Header>
        <Card.Body className="text-center">
          <Spinner />
        </Card.Body>
      </Card>
    );
  }

  if (deliveryDays.length === 0) {
    return (
      <Card>
        <Card.Header>
          <h5 className="mb-0">Lieblingsbrote</h5>
        </Card.Header>
        <Card.Body>
          <p className="text-muted mb-0">Keine Liefertage konfiguriert.</p>
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card>
      <Card.Header>
        <h5 className="mb-0">Lieblingsbrote – KW {week}</h5>
      </Card.Header>
      <Card.Body>
        {deliveryDays.map((day) => (
          <div key={day} className="mb-4">
            <h6>{DAY_LABELS[day] || `Tag ${day}`}</h6>
            <PreferredBreadStatisticsCard
              year={year}
              week={week}
              deliveryDay={day}
              csrfToken="no_token"
            />
          </div>
        ))}
      </Card.Body>
    </Card>
  );
};

export default DashboardPreferredBreadStats;
