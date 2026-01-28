import React, { useState } from "react";
import { Accordion, Col, Form, Nav, Row } from "react-bootstrap";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import {
  DeliveryCycleEnum,
  GrowingPeriod,
  NoticePeriodUnitEnum,
  type ProductTypeAccordionInBestellWizard,
} from "../api-client";
import dayjs from "dayjs";
import TapirButton from "../components/TapirButton.tsx";
import { getNoticePeriodUnitDisplay } from "./getNoticePeriodUnitDispay.ts";

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
  noticePeriodDuration: number | undefined;
  setNoticePeriodDuration: (noticePeriod: number) => void;
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
  accordions: ProductTypeAccordionInBestellWizard[];
  setAccordions: (accordions: ProductTypeAccordionInBestellWizard[]) => void;
  titleBestellWizardProductChoices: string;
  setTitleBestellWizardProductChoices: (title: string) => void;
  titleBestellWizardIntro: string;
  setTitleBestellWizardIntro: (title: string) => void;
  backgroundImageInBestellWizard: string;
  setBackgroundImageInBestellWizard: (title: string) => void;
  setNoticePeriodEnabled: (enabled: boolean) => void;
  noticePeriodEnabled: boolean;
  noticePeriodUnit: NoticePeriodUnitEnum;
  setNoticePeriodUnit: (unit: NoticePeriodUnitEnum) => void;
  canUpdateNoticePeriod: boolean;
}

type Tab = "general" | "contracts" | "bestell_wizard";

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
  noticePeriodDuration,
  setNoticePeriodDuration,
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
  accordions,
  setAccordions,
  titleBestellWizardProductChoices,
  setTitleBestellWizardProductChoices,
  titleBestellWizardIntro,
  setTitleBestellWizardIntro,
  backgroundImageInBestellWizard,
  setBackgroundImageInBestellWizard,
  noticePeriodEnabled,
  setNoticePeriodEnabled,
  noticePeriodUnit,
  setNoticePeriodUnit,
  canUpdateNoticePeriod,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>("general");

  function setAccordionTitle(title: string, index: number) {
    accordions[index].title = title;
    setAccordions([...accordions]);
  }

  function setAccordionDescription(description: string, index: number) {
    accordions[index].description = description;
    setAccordions([...accordions]);
  }

  function moveAccordionUp(indexToMoveUp: number) {
    swapAccordionIndexes(indexToMoveUp, indexToMoveUp - 1);
  }

  function moveAccordionDown(indexToMoveDown: number) {
    swapAccordionIndexes(indexToMoveDown, indexToMoveDown + 1);
  }

  function swapAccordionIndexes(indexA: number, indexB: number) {
    const accordionA = accordions[indexA];
    const accordionB = accordions[indexB];

    accordions[indexB] = accordionA;
    accordions[indexA] = accordionB;

    setAccordions([...accordions]);
  }

  return (
    <>
      <Row>
        <Col>
          <Nav
            fill
            variant={"tabs"}
            onSelect={(selectedKey) => setActiveTab(selectedKey as Tab)}
            defaultActiveKey={"general"}
          >
            <Nav.Item>
              <Nav.Link eventKey="general">Allgemein</Nav.Link>
            </Nav.Item>
            <Nav.Item>
              <Nav.Link eventKey="contracts">Verträge</Nav.Link>
            </Nav.Item>
            <Nav.Item>
              <Nav.Link eventKey="bestell_wizard">BestellWizard</Nav.Link>
            </Nav.Item>
          </Nav>
        </Col>
      </Row>
      <Row>
        {activeTab === "general" && (
          <>
            <Col>
              <Row className={"mt-2"}>
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
              <Row className={"mt-4"}>
                <Form.Group controlId={"capacity"}>
                  <Form.Label>
                    Produkt Kapazität in Produkt-Größe für die Vertragsperiode{" "}
                    {formatDateNumeric(growingPeriod?.startDate)} bis{" "}
                    {formatDateNumeric(growingPeriod?.endDate)}
                  </Form.Label>
                  <Form.Control
                    type={"number"}
                    onChange={(event) =>
                      setCapacity(Number.parseFloat(event.target.value))
                    }
                    required={true}
                    value={capacity}
                  />
                </Form.Group>
              </Row>
              {showJokers && (
                <Row className={"mt-4"}>
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

              <Row className={"mt-4"}>
                <Form.Group controlId={"delivery_cycle"}>
                  <Form.Label>Liefer-/Abholzyklus</Form.Label>
                  <Form.Select
                    onChange={(event) =>
                      setDeliveryCycle(event.target.value as DeliveryCycleEnum)
                    }
                    required={true}
                    value={deliveryCycle}
                  >
                    {Object.entries(deliveryCycleOptions).map(
                      ([key, value]) => {
                        return (
                          <option key={key} value={key}>
                            {value}
                          </option>
                        );
                      },
                    )}
                  </Form.Select>
                </Form.Group>
              </Row>
            </Col>
          </>
        )}
        {activeTab === "contracts" && (
          <>
            <Col>
              {showNoticePeriod && (
                <Row className={"mt-2"}>
                  <Form.Group controlId={"notice_period_enabled"}>
                    <Form.Label></Form.Label>
                    <Form.Check
                      label={"Kündigungsfrist überschrieben"}
                      onChange={(event) =>
                        setNoticePeriodEnabled(event.target.checked)
                      }
                      required={false}
                      checked={noticePeriodEnabled}
                      disabled={!canUpdateNoticePeriod}
                    />
                    <Form.Text>
                      Ob dieses Produkt-Typ ein andere Kündigungsfrist nutzen
                      soll als die aus der allgemeine Konfig. Wenn du diese
                      Option einsetzen willst, wende dich an der Admins.
                    </Form.Text>
                  </Form.Group>
                </Row>
              )}
              {showNoticePeriod && noticePeriodEnabled && (
                <Row className={"mt-2"}>
                  <Form.Group controlId={"notice_period_duration"}>
                    <Form.Label>Kündigungsfrist Dauer</Form.Label>
                    <Form.Control
                      type={"number"}
                      onChange={(event) =>
                        setNoticePeriodDuration(
                          Number.parseInt(event.target.value),
                        )
                      }
                      required={true}
                      value={noticePeriodDuration}
                      disabled={!canUpdateNoticePeriod}
                    />
                  </Form.Group>
                </Row>
              )}
              {showNoticePeriod && noticePeriodEnabled && (
                <Row className={"mt-2"}>
                  <Form.Group controlId={"notice_period_unit"}>
                    <Form.Label>Kündigungsfrist Einheit</Form.Label>

                    <Form.Select
                      onChange={(event) =>
                        setNoticePeriodUnit(
                          event.target.value as NoticePeriodUnitEnum,
                        )
                      }
                      required={true}
                      value={noticePeriodUnit}
                      disabled={!canUpdateNoticePeriod}
                    >
                      {Object.values(NoticePeriodUnitEnum).map((value) => (
                        <option key={value} value={value}>
                          {getNoticePeriodUnitDisplay(value)}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Row>
              )}
              <Row className={"mt-4"}>
                <Form.Group controlId={"tax_rate"}>
                  <Form.Label>Mehrwertsteuersatz</Form.Label>
                  <Form.Control
                    type={"number"}
                    onChange={(event) =>
                      setTaxRate(Number.parseFloat(event.target.value))
                    }
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
            </Col>
            <Col>
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
                    onChange={(event) =>
                      setMustBeSubscribedTo(event.target.checked)
                    }
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
                    onChange={(event) =>
                      setForceWaitingList(event.target.checked)
                    }
                    required={false}
                    checked={forceWaitingList}
                    label={"Warteliste-Modus"}
                  />
                  <Form.Text>
                    Wenn aktiviert, können bestehende Mitglieder und neue
                    Interessenten keine neuen {name} buchen, unabhängig davon,
                    ob es freie Kapazitäten gäbe. Wenn nicht aktiviert, können{" "}
                    {name} nur gebucht werden, wenn es gemäß automatisierter
                    Berechnung genug Kapazitäten gibt.
                  </Form.Text>
                </Form.Group>
              </Row>
            </Col>
          </>
        )}
        {activeTab === "bestell_wizard" && (
          <>
            <Col>
              <Row className={"mt-2"}>
                <Form.Group controlId={"description_bestellwizard_short"}>
                  <Form.Label>
                    Beschreibung im Bestellwizard bei der erste Seite
                    (Produkt-Typ Auswahl)
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
              <Row className={"mt-4"}>
                <Form.Group controlId={"description_bestellwizard_long"}>
                  <Form.Label>
                    Beschreibung im Bestellwizard bei der Produkt-Spezifische
                    Seite
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
              <Row className={"mt-4"}>
                <Form.Group controlId={"order_in_bestellwizard"}>
                  <Form.Label>
                    Reihenfolge im BestellWizard (kleiner ist früher)
                  </Form.Label>
                  <Form.Control
                    type={"number"}
                    onChange={(event) =>
                      setOrderInBestellwizard(
                        Number.parseInt(event.target.value),
                      )
                    }
                    required={true}
                    value={orderInBestellwizard}
                    step={1}
                  />
                </Form.Group>
              </Row>

              <Row className={"mt-4"}>
                <Form.Group controlId={"title_bestellwizard"}>
                  <Form.Label>
                    Titel im BestellWizard bei der Produkt-Größe-Auswahl
                  </Form.Label>
                  <Form.Control
                    type={"text"}
                    onChange={(event) =>
                      setTitleBestellWizardProductChoices(event.target.value)
                    }
                    required={true}
                    value={titleBestellWizardProductChoices}
                  />
                </Form.Group>
              </Row>

              <Row className={"mt-4"}>
                <Form.Group controlId={"title_bestellwizard"}>
                  <Form.Label>
                    Titel im BestellWizard bei der Produkt-Typ-Intro
                  </Form.Label>
                  <Form.Control
                    type={"text"}
                    onChange={(event) =>
                      setTitleBestellWizardIntro(event.target.value)
                    }
                    required={true}
                    value={titleBestellWizardIntro}
                  />
                </Form.Group>
              </Row>
            </Col>
            <Col>
              <Row className={"mt-2"}>
                <Accordion>
                  {accordions.map((accordion, index) => (
                    <Accordion.Item
                      eventKey={index.toString()}
                      key={index.toString()}
                    >
                      <Accordion.Header>{accordion.title}</Accordion.Header>
                      <Accordion.Body>
                        <Form.Group controlId={"accordion_title_" + index}>
                          <Form.Label>Akkordeon {index + 1} - Titel</Form.Label>
                          <Form.Control
                            type={"text"}
                            onChange={(event) =>
                              setAccordionTitle(event.target.value, index)
                            }
                            required={true}
                            value={accordion.title}
                          />
                        </Form.Group>
                        <Form.Group
                          controlId={"accordion_description_" + index}
                        >
                          <Form.Label>Akkordeon {index + 1} - Text</Form.Label>
                          <Form.Control
                            type={"text"}
                            onChange={(event) =>
                              setAccordionDescription(event.target.value, index)
                            }
                            required={true}
                            value={accordion.description}
                          />
                        </Form.Group>
                        <div className={"mt-2 d-flex flew-row gap-2"}>
                          <TapirButton
                            variant={"outline-danger"}
                            icon={"delete"}
                            text={"Akkordeon entfernen"}
                            onClick={() =>
                              setAccordions(
                                accordions.filter((_, i) => i !== index),
                              )
                            }
                          />
                          <TapirButton
                            icon={"arrow_drop_up"}
                            variant={"outline-secondary"}
                            disabled={index === 0}
                            onClick={() => moveAccordionUp(index)}
                          />
                          <TapirButton
                            icon={"arrow_drop_down"}
                            variant={"outline-secondary"}
                            disabled={index === accordions.length - 1}
                            onClick={() => moveAccordionDown(index)}
                          />
                        </div>
                      </Accordion.Body>
                    </Accordion.Item>
                  ))}
                </Accordion>
                <Row className={"mt-2"}>
                  <Col>
                    <TapirButton
                      variant={"outline-secondary"}
                      text={"Akkordeon hinzufügen"}
                      icon={"add_circle"}
                      onClick={() =>
                        setAccordions([
                          ...accordions,
                          {
                            title: "Titel",
                            description: "Beschreibung",
                            order: accordions.length,
                          },
                        ])
                      }
                    />
                  </Col>
                </Row>
              </Row>
              <Row className={"mt-4"}>
                <Form.Group controlId={"background_image_bestellwizard"}>
                  <Form.Label>Hintergrundbild im BestellWizard</Form.Label>
                  <Form.Control
                    type={"text"}
                    onChange={(event) =>
                      setBackgroundImageInBestellWizard(event.target.value)
                    }
                    required={true}
                    value={backgroundImageInBestellWizard}
                  />
                </Form.Group>
              </Row>
              <Row className={"mt-4"}>
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
          </>
        )}
      </Row>
    </>
  );
};

export default ProductTypeForm;
