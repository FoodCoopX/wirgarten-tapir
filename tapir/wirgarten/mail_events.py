class Events:
    REGISTER_MEMBERSHIP_AND_SUBSCRIPTION = "register_membership_and_subscription"

    # Absenden Bestellwizzard Mitgliedschaft (nur Geno-Anteile)
    REGISTER_MEMBERSHIP_ONLY = "register_membership_only"

    # Vertragsänderungen im Mitgliederbereich (Erntevertrag erhöhen, dazubestellen, abbestellen, kündigen, nicht verlängern, verlängern, Abholort ändern)
    MEMBERAREA_CHANGE_CONTRACT = "memberarea_change_contract"

    # Mitgliedsdatenänderungen (e-Mail-Adresse, Bankdaten, Adresse)
    MEMBERAREA_CHANGE_DATA = "memberarea_change_data"

    # Mitglied kündigt im Probemonat
    TRIAL_CANCELLATION = "trial_cancellation"

    # Mitglied hat Vertrag explizit nicht verlängert
    CONTRACT_NOT_RENEWED = "contract_not_renewed"

    # Mitglied tritt der Genossenschaft bei (nach Ablauf der Probezeit)
    MEMBERSHIP_ENTRY = "membership_entry"

    # Letzte Abholung (es gibt keine weiteren Verträge mehr)
    FINAL_PICKUP = "final_pickup"

    # Mitglied hat Abholort geändert
    MEMBERAREA_CHANGE_PICKUP_LOCATION = "memberarea_change_pickup_location"

    # Mitglied möchte Email Adresse ändern, muss Bestätigungslink klicken
    MEMBERAREA_CHANGE_EMAIL_INITIATE = "memberarea_change_email_initiate"

    # Mitglied möchte Email Adresse ändern, hinweis wird an der neue Adresse geschickt das er die alte Adresse lesen soll
    MEMBERAREA_CHANGE_EMAIL_HINT = "memberarea_change_email_hint"

    # Email Adresse wurde erfolgreich geändert
    MEMBERAREA_CHANGE_EMAIL_SUCCESS = "memberarea_change_email_success"

    CONTRACT_CANCELLED = "contract_canceled"

    CONFIRMATION_REGISTRATION_IN_WAITING_LIST = (
        "confirmation_registration_in_waiting_list"
    )

    WAITING_LIST_WISH_CAN_BE_ORDERED = "waiting_list_wish_can_be_ordered"
