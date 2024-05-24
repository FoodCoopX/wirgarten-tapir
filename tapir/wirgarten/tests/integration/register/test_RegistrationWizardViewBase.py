from django.core.validators import MinValueValidator, URLValidator
from django.template.response import TemplateResponse
from formtools.wizard.views import StepsHelper
from icecream import ic

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import parameter_definition, ParameterMeta
from tapir.wirgarten.models import Product, ProductType
from tapir.wirgarten.parameters import Parameter, ParameterCategory
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestRegistrationWizardViewBase(TapirIntegrationTest):
    def setUp(self):
        product: Product = ProductFactory.create()
        parameter_definition(
            key=Parameter.COOP_BASE_PRODUCT_TYPE,
            label="Basis Produkttyp",
            datatype=TapirParameterDatatype.STRING,
            initial_value=product.type.id,
            description="Der Basis Produkttyp.",
            category=ParameterCategory.COOP,
            meta=ParameterMeta(
                options=list(map(lambda x: (x.id, x.name), ProductType.objects.all()))
            ),
        )

        parameter_definition(
            key=Parameter.COOP_MIN_SHARES,
            label="Mindestanzahl Genossenschaftsanteile",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Die Mindestanzahl der Genossenschaftsanteile die ein neues Mitglied zeichnen muss.",
            category=ParameterCategory.COOP,
            order_priority=1000,
            meta=ParameterMeta(validators=[MinValueValidator(limit_value=0)]),
        )

        parameter_definition(
            key=Parameter.COOP_STATUTE_LINK,
            label="Link zur Satzung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/satzung",
            description="Der Link zur Satzung der Genossenschaft.",
            category=ParameterCategory.COOP,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

    def test_RegistrationWizardViewBase_currentGrowingPeriodIsFull_showsWaitingList(
        self,
    ):
        response: TemplateResponse = self.client.get("/wirgarten/register")
        steps_helper: StepsHelper = response.context_data["wizard"]["steps"]
        ic(steps_helper)
        ic(steps_helper.all)
        self.assertNotIn("coop_shares", steps_helper.all)
