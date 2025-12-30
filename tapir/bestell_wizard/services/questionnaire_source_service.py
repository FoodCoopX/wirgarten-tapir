from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import QuestionaireTrafficSourceOption
from tapir.wirgarten.parameter_keys import ParameterKeys


class QuestionnaireSourceService:
    @classmethod
    def get_questionnaire_source_choices(cls, cache: dict):
        channel_names = [
            channel.strip()
            for channel in get_parameter_value(
                key=ParameterKeys.ORGANISATION_QUESTIONAIRE_SOURCES,
                cache=cache,
            ).split(",")
        ]

        return {
            QuestionaireTrafficSourceOption.objects.get_or_create(name=name)[0].id: name
            for name in channel_names
        }
