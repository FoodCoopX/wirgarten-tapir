# Glossary

Domain terms, their names in the code and in the German frontend. Use these names in new or changed code, texts and
documentation.
The current code and frontend may not match these recommendations. Update files you change.

| Code                                | German (frontend)     | Meaning                                                                                                            |
|-------------------------------------|-----------------------|--------------------------------------------------------------------------------------------------------------------|
| contract                            | Doesn't show up       | Anything with regular payments: subscription, solidarity contribution, association membership                      |
| subscription (`Subscription`)       | Vertrag               | A contract tied to a product, with a quantity                                                                      |
| product type (`ProductType`)        | Produktanteil         | A category of products, e.g. Ernteanteile                                                                          |
| product (`Product`)                 | Anteilsgröße          | A size within a product type, e.g. S, M, L                                                                         |
| growing period (`GrowingPeriod`)    | Vertragsperiode       | The period subscriptions start and end in                                                                          |
| coop share (`CoopShareTransaction`) | Genossenschaftsanteil | A share of the cooperative; always `coop_share` in code, never just `share` to avoid confusion with product shares |
| pickup location (`PickupLocation`)  | Abholort              | Where the member picks up deliveries                                                                               |
| solidarity contribution             | Solidarbeitrag        | Voluntary monthly amount on top of or below the subscription prices                                                |
| trial period                        | Probezeit             | Period after a subscription start during which the member can cancel at short notice                               |
