BASE_PRODUCT_NAME = "Ernteanteile"

COOP_SHARE_PRICE = 50.0

# define the custom views from the site module
VIEWS = {
    "draftuser_register": "tapir.wirgarten_site.registration.views.RegistrationView",
    "draftuser_confirm_registration": "tapir.lueneburg.registration.views.RegistrationWizardConfirmView",
    "admin_dashboard": "tapir.wirgarten.views.admin_dashboard.AdminDashboardView",
    "admin_dashboard_cashflow_data": "tapir.wirgarten.views.admin_dashboard.get_cashflow_chart_data",
}

REGISTRATION_STEPS = {
    "base_product": {
        "title": "Ernteanteile",
        "description": "Erntevertrag - Wieviel Gemüse möchtest du jede Woche bekommen?",
        "intro_template": "registration/steps/base_product.intro.html",
        "outro_template": "registration/steps/base_product.outro.html",
    },
    "base_product_not_available": {
        "title": "Ernteanteile",
        "description": "Erntevertrag - Wieviel Gemüse möchtest du jede Woche bekommen?",
        "intro_template": "registration/steps/harvest_shares_no_subscription.intro.html",
    },
    "coop_shares": {
        "title": "Genossenschaft",
        "description": "Genossenschaft - Mit wie vielen Genossenschaftsanteilen möchtest du dich an deinem WirGarten beteiligen?",
        "intro_template": "registration/steps/coop_shares.intro.html",
        "outro_template": "registration/steps/coop_shares.outro.html",
    },
    "coop_shares_not_available": {
        "title": "Genossenschaftsanteile",
        "description": "Genossenschaft - Mit wie vielen Genossenschaftsanteilen möchtest du dich an deinem WirGarten beteiligen?",
        "intro_template": "registration/steps/coop_shares_not_available.intro.html",
    },
    "additional_product_Hühneranteile": {
        "title": "Zusatzabo",
        "description": "Zusatzabo - Willst du einen Hühneranteil mit Eiern?",
        "intro_template": "registration/steps/chicken_shares.intro.html",
    },
    "additional_product_BestellCoop": {
        "title": "BestellCoop",
        "description": "BestellCoop - Möchtest du regelmäßig Grundnahrungsmittel in großen Mengen bestellen?",
        "intro_template": "registration/steps/bestellcoop.intro.html",
    },
    "additional_product_Brot": {
        "title": "Brot",
        "description": "Willst du einen Brot-Zusatzanteil?",
        "intro_template": "registration/steps/bread.intro.html",
    },
    "additional_product_Honig": {
        "title": "Honig",
        "description": "Willst du einen Honig-Zusatzanteil?",
        "intro_template": "registration/steps/honey.intro.html",
    },
    "additional_product_Leinöl": {
        "title": "Leinöl",
        "description": "Willst du einen Leinöl-Zusatzanteil?",
        "intro_template": "registration/steps/oil.intro.html",
    },
    "pickup_location": {
        "title": "Abholort",
        "description": "Abholort - Wo möchtest du dein Gemüse abholen?",
    },
    "summary": {
        "title": "Übersicht",
        "description": "Übersicht",
    },
    "personal_details": {
        "title": "Persönliche Daten",
        "description": "Vertragsabschluss - Jetzt fehlen nur noch deine persönlichen Daten!",
    },
}
