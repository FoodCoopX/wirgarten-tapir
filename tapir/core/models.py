from functools import partial

from django.db import models
from nanoid import generate

ID_LENGTH = 10


def generate_id():
    return generate(size=ID_LENGTH)


class TapirModel(models.Model):
    id = models.CharField(
        "ID",
        max_length=ID_LENGTH,
        unique=True,
        primary_key=True,
        default=partial(generate_id),
    )

    class Meta:
        abstract = True


class SidebarLinkGroup:
    name: str
    links: []

    def __init__(self, name: str):
        self.name = name
        self.links = []

    def add_link(self, display_name: str, material_icon: str, url: str, html_id=""):
        self.links.append(
            {
                "url": url,
                "display_name": display_name,
                "material_icon": material_icon,
                "html_id": html_id,
            }
        )
