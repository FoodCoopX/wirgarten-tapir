from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class BestellWizardStyleService:
    @classmethod
    def build_body_style(cls, cache: dict) -> str:
        background_color = get_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_BACKGROUND_COLOR, cache=cache
        )
        body_style = f"background-color: {background_color}"

        background_image_url = get_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_BACKGROUND_IMAGE, cache=cache
        )
        if background_image_url:
            body_style = (
                f"background-image: url({background_image_url}); "
                "background-repeat: repeat; background-position: center;"
            )

        return body_style
