import React, { useState, useEffect } from "react";
import { Card, Spinner } from "react-bootstrap";
import { BakeryApi } from "../api-client";
import { useApi } from "../hooks/useApi";
import { PreferredBreadStatisticsCard } from "../bakery/components/cards/PreferredBreadStatisticsCard";
import dayjs from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";

dayjs.extend(isoWeek);

const DAY_LABELS: Record<number, string> = {
  0: "Montag",
  1: "Dienstag",
  2: "Mittwoch",
  3: "Donnerstag",
  4: "Freitag",
  5: "Samstag",
  6: "Sonntag",
};

const DashboardPreferredBreadStats: React.FC = () => {
  const bakeryApi = useApi(BakeryApi, "no_token");
  const [deliveryDays, setDeliveryDays] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  const year = dayjs().isoWeekYear();
  const week = dayjs().isoWeek();

  useEffect(() => {
    bakeryApi
      .pickupLocationsApiDeliveryDaysRetrieve()
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
