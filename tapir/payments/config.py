PAYMENT_TYPE_COOP_SHARES = "Genossenschaftsanteile"


class IntendedUseTokens:
    SITE_NAME = "betriebsname"
    FIRST_NAME = "vorname"
    LAST_NAME = "nachname"
    MEMBER_NUMBER_SHORT = "mitgliedsnummer_kurz"
    MEMBER_NUMBER_LONG = "mitgliedsnummer_lang"
    MEMBER_NUMBER_WITHOUT_PREFIX = "mitgliedsnummer_ohne_prefix"
    NUMBER_OF_COOP_SHARES = "anzahl_geno_anteile"
    COOP_ENTRY_DATE = "beitrittsdatum"
    PRICE_SINGLE_SHARE = "preis_einzelne_geno_anteil"
    MONTHLY_PRICE_CONTRACTS_WITHOUT_SOLI = "monatsbeitrag_ohne_soli"
    MONTHLY_PRICE_CONTRACTS_WITH_SOLI = "monatsbeitrag_mit_soli"
    MONTHLY_PRICE_JUST_SOLI = "monatsbeitrag_nur_soli"
    TOTAL_PRICE_CONTRACTS_WITHOUT_SOLI = "gesamtbeitrag_ohne_soli"
    TOTAL_PRICE_CONTRACTS_WITH_SOLI = "gesamtbeitrag_mit_soli"
    TOTAL_PRICE_JUST_SOLI = "gesamtbeitrag_nur_soli"
    CONTRACT_LIST = "vertragsliste"
    PAYMENT_RHYTHM = "zahlungsintervall"

    COMMON_TOKENS = [
        SITE_NAME,
        FIRST_NAME,
        LAST_NAME,
        MEMBER_NUMBER_SHORT,
        MEMBER_NUMBER_LONG,
        MEMBER_NUMBER_WITHOUT_PREFIX,
    ]

    COOP_SHARE_TOKENS = [NUMBER_OF_COOP_SHARES, COOP_ENTRY_DATE, PRICE_SINGLE_SHARE]

    CONTRACT_TOKENS = [
        MONTHLY_PRICE_CONTRACTS_WITHOUT_SOLI,
        MONTHLY_PRICE_CONTRACTS_WITH_SOLI,
        MONTHLY_PRICE_JUST_SOLI,
        TOTAL_PRICE_CONTRACTS_WITHOUT_SOLI,
        TOTAL_PRICE_CONTRACTS_WITH_SOLI,
        TOTAL_PRICE_JUST_SOLI,
        CONTRACT_LIST,
        PAYMENT_RHYTHM,
    ]
