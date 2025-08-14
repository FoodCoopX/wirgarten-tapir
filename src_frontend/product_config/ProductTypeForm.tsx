import React from "react";
import { Col, Form, Row } from "react-bootstrap";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { DeliveryCycleEnum, GrowingPeriod } from "../api-client";
import dayjs from "dayjs";

interface ProductTypeFormProps {
  name: string;
  setName: (name: string) => void;
  iconLink: string;
  setIconLink: (iconLink: string) => void;
  growingPeriod: GrowingPeriod;
  capacity: number;
  setCapacity: (capacity: number) => void;
  deliveryCycle: DeliveryCycleEnum;
  setDeliveryCycle: (cycle: DeliveryCycleEnum) => void;
  deliveryCycleOptions: { [key: string]: string };
  showJokers: boolean;
  isAffectedByJokers: boolean;
  setIsAffectedByJokers: (affected: boolean) => void;
  showNoticePeriod: boolean;
  noticePeriod: number | undefined;
  setNoticePeriod: (noticePeriod: number) => void;
  taxRate: number;
  setTaxRate: (taxRate: number) => void;
  taxRateChangeDate: Date;
  setTaxRateChangeDate: (date: Date) => void;
  singleSubscriptionOnly: boolean;
  setSingleSubscriptionOnly: (single: boolean) => void;
  mustBeSubscribedTo: boolean;
  setMustBeSubscribedTo: (mustBeSubscribedTo: boolean) => void;
  showAssociationMembership: boolean;
  isAssociationMembership: boolean;
  setIsAssociationMembership: (is: boolean) => void;
  descriptionBestellwizardShort: string;
  setDescriptionBestellwizardShort: (short: string) => void;
  descriptionBestellwizardLong: string;
  setDescriptionBestellwizardLong: (long: string) => void;
  orderInBestellwizard: number;
  setOrderInBestellwizard: (orderInBestellWizard: number) => void;
  contractLink: string;
  setContractLink: (contractLink: string) => void;
  forceWaitingList: boolean;
  setForceWaitingList: (forceWaitingList: boolean) => void;
}

const ProductTypeForm: React.FC<ProductTypeFormProps> = ({
  name,
  setName,
  iconLink,
  setIconLink,
  growingPeriod,
  capacity,
  setCapacity,
  deliveryCycle,
  setDeliveryCycle,
  deliveryCycleOptions,
  showJokers,
  isAffectedByJokers,
  setIsAffectedByJokers,
  showNoticePeriod,
  noticePeriod,
  setNoticePeriod,
  taxRate,
  setTaxRate,
  taxRateChangeDate,
  setTaxRateChangeDate,
  singleSubscriptionOnly,
  setSingleSubscriptionOnly,
  mustBeSubscribedTo,
  setMustBeSubscribedTo,
  showAssociationMembership,
  isAssociationMembership,
  setIsAssociationMembership,
  descriptionBestellwizardShort,
  setDescriptionBestellwizardShort,
  descriptionBestellwizardLong,
  setDescriptionBestellwizardLong,
  orderInBestellwizard,
  setOrderInBestellwizard,
  contractLink,
  setContractLink,
  forceWaitingList,
  setForceWaitingList,
}) => {
  return (
    <Row>
      <Col>
        <Row>
          <h5>Allgemein</h5>
        </Row>
        <Row>
          <Form.Group controlId={"name"}>
            <Form.Label>Name</Form.Label>
            <Form.Control
              type={"text"}
              placeholder={"Name"}
              onChange={(event) => setName(event.target.value)}
              required={true}
              value={name}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"iconLink"}>
            <Form.Label>Icon Link</Form.Label>
            <Form.Control
              type={"text"}
              placeholder={"Icon Link"}
              onChange={(event) => setIconLink(event.target.value)}
              required={true}
              value={iconLink}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"capacity"}>
            <Form.Label>
              Produkt Kapazität in Produkt-Größe für die Vertragsperiode{" "}
              {formatDateNumeric(growingPeriod?.startDate)} bis{" "}
              {formatDateNumeric(growingPeriod?.endDate)}
            </Form.Label>
            <Form.Control
              type={"number"}
              onChange={(event) => setCapacity(parseFloat(event.target.value))}
              required={true}
              value={capacity}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"delivery_cycle"}>
            <Form.Label>Liefer-/Abholzyklus</Form.Label>
            <Form.Select
              onChange={(event) =>
                setDeliveryCycle(event.target.value as DeliveryCycleEnum)
              }
              required={true}
              value={deliveryCycle}
            >
              {Object.entries(deliveryCycleOptions).map(([key, value]) => {
                return (
                  <option key={key} value={key}>
                    {value}
                  </option>
                );
              })}
            </Form.Select>
          </Form.Group>
        </Row>
        {showJokers && (
          <Row className={"mt-2"}>
            <Form.Group controlId={"is_affected_by_jokers"}>
              <Form.Check
                onChange={(event) =>
                  setIsAffectedByJokers(event.target.checked)
                }
                required={false}
                checked={isAffectedByJokers}
                label={"Nimmt am Joker-Verfahren teil"}
              />
            </Form.Group>
          </Row>
        )}
      </Col>
      <Col>
        <Row>
          <h5>Verträge</h5>
        </Row>
        {showNoticePeriod && (
          <Row>
            <Form.Group controlId={"notice_period"}>
              <Form.Label>Kündigungsfrist</Form.Label>
              <Form.Control
                type={"number"}
                onChange={(event) =>
                  setNoticePeriod(parseInt(event.target.value))
                }
                required={true}
                value={noticePeriod}
              />
              <Form.Text>Anzahl an Monate</Form.Text>
            </Form.Group>
          </Row>
        )}
        <Row className={"mt-2"}>
          <Form.Group controlId={"tax_rate"}>
            <Form.Label>Mehrwertsteuersatz</Form.Label>
            <Form.Control
              type={"number"}
              onChange={(event) => setTaxRate(parseFloat(event.target.value))}
              required={true}
              value={taxRate}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"tax_rate_change_date"}>
            <Form.Label>Neuer Mehrwertsteuersatz gültig ab</Form.Label>
            <Form.Control
              type={"date"}
              onChange={(event) =>
                setTaxRateChangeDate(new Date(event.target.value))
              }
              required={true}
              value={dayjs(taxRateChangeDate).format("YYYY-MM-DD")}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"single_subscription_only"}>
            <Form.Check
              onChange={(event) =>
                setSingleSubscriptionOnly(event.target.checked)
              }
              required={false}
              checked={singleSubscriptionOnly}
              label={"Nur Einzelabonnement möglich"}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"must_be_subscribed_to"}>
            <Form.Check
              onChange={(event) => setMustBeSubscribedTo(event.target.checked)}
              required={false}
              checked={mustBeSubscribedTo}
              label={"Ist Pflicht"}
            />
          </Form.Group>
        </Row>
        {showAssociationMembership && (
          <Row className={"mt-2"}>
            <Form.Group controlId={"is_association_membership"}>
              <Form.Check
                onChange={(event) =>
                  setIsAssociationMembership(event.target.checked)
                }
                required={false}
                checked={isAssociationMembership}
                label={"Ist die Vereinsmitgliedschaft"}
              />
            </Form.Group>
          </Row>
        )}
        <Row className={"mt-2"}>
          <Form.Group controlId={"force_waiting_list"}>
            <Form.Check
              onChange={(event) => setForceWaitingList(event.target.checked)}
              required={false}
              checked={forceWaitingList}
              label={"Warteliste-Modus"}
            />
            <Form.Text>
              Wenn aktiviert, können bestehende Mitglieder und neue
              Interessenten keine neuen {name} buchen, unabhängig davon, ob es
              freie Kapazitäten gäbe. Wenn nicht aktiviert, können {name} nur
              gebucht werden, wenn es gemäß automatisierter Berechnung genug
              Kapazitäten gibt.
            </Form.Text>
          </Form.Group>
        </Row>
      </Col>
      <Col>
        <h5>BestellWizard</h5>
        <Row>
          <Form.Group controlId={"description_bestellwizard_short"}>
            <Form.Label>
              Beschreibung im Bestellwizard bei der erste Seite (Produkt-Typ
              Auswahl)
            </Form.Label>
            <Form.Control
              type={"text"}
              onChange={(event) =>
                setDescriptionBestellwizardShort(event.target.value)
              }
              required={true}
              value={descriptionBestellwizardShort}
              as={"textarea"}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"description_bestellwizard_long"}>
            <Form.Label>
              Beschreibung im Bestellwizard bei der Produkt-Spezifische Seite
            </Form.Label>
            <Form.Control
              type={"text"}
              onChange={(event) =>
                setDescriptionBestellwizardLong(event.target.value)
              }
              required={true}
              value={descriptionBestellwizardLong}
              as={"textarea"}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"order_in_bestellwizard"}>
            <Form.Label>
              Reihenfolge im BestellWizard (kleiner ist früher)
            </Form.Label>
            <Form.Control
              type={"number"}
              onChange={(event) =>
                setOrderInBestellwizard(parseInt(event.target.value))
              }
              required={true}
              value={orderInBestellwizard}
              step={1}
            />
          </Form.Group>
        </Row>
        <Row className={"mt-2"}>
          <Form.Group controlId={"contract_link"}>
            <Form.Label>Link zu den Vertragsgrundsätzen</Form.Label>
            <Form.Control
              type={"text"}
              onChange={(event) => setContractLink(event.target.value)}
              required={true}
              value={contractLink}
            />
          </Form.Group>
        </Row>
      </Col>
    </Row>
  );
};

export default ProductTypeForm;
