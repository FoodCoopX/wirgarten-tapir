import copy
import html
import json
import subprocess
import tempfile

from bs4 import BeautifulSoup
from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from lxml import etree


def _extract_fonts(mjml: str):
    soup = BeautifulSoup(mjml, "xml")
    font_elements = [
        font_element.extract() for font_element in soup.find_all("mj-font")
    ]
    fonts = [font_element["href"] for font_element in font_elements]
    return fonts


def mjml2html(mjml: str) -> str:
    fonts = _extract_fonts(mjml)

    cmd_args = copy.copy(settings.MJML_EXEC_CMD)
    if not isinstance(cmd_args, list):
        cmd_args = [cmd_args]
    for ca in ("-i", "-s"):
        if ca not in cmd_args:
            cmd_args.append(ca)

    if fonts:
        cmd_args.extend(["--config.fonts", json.dumps(fonts)])

    with tempfile.SpooledTemporaryFile(max_size=(5 * 1024 * 1024)) as stdout_tmp_f:
        try:
            p = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=stdout_tmp_f,
                stderr=subprocess.PIPE,
            )
            stderr = p.communicate(force_bytes(mjml))[1]
        except (IOError, OSError) as e:
            cmd_str = " ".join(cmd_args)
            raise RuntimeError(
                f'Problem to run command "{cmd_str}"\n'
                f"{e}\n"
                "Check that mjml is installed and allow permissions to execute.\n"
                "See https://github.com/mjmlio/mjml#installation"
            ) from e
        stdout_tmp_f.seek(0)
        stdout = stdout_tmp_f.read()

    if stderr:
        raise RuntimeError(f"MJML stderr is not empty: {force_str(stderr)}.")

    return force_str(stdout)
