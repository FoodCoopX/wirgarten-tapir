from django.forms import Form, ModelForm
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.forms.form_mixins import FormWithRequestMixin


@require_http_methods(["GET", "POST"])
def get_form_modal(
    request,
    form_class: type[Form | ModelForm],
    handler,
    instance=None,
    redirect_url_resolver=(lambda x: str),
    **kwargs
):
    """
    Generic view to handle a modal form.

    :param request: The request object.
    :param form_class: The class of the form to be displayed.
    :param handler: The handler to be called when the form is submitted.
    :param instance: The instance to be edited.
    :param redirect_url_resolver: A function to resolve the redirect url after submitting. Gets the handler result as parameter.
    """

    if issubclass(form_class, FormWithRequestMixin):
        kwargs.update({"request": request})

    # if this is a POST request we need to process the modal data
    if request.method == "POST":
        # create a modal instance and populate it with data from the request:
        form = (
            form_class(request.POST, instance=instance, **kwargs)
            if instance
            else form_class(request.POST, **kwargs)
        )

        # check whether it's valid:
        if form.is_valid():
            # process the data in modal.cleaned_data as required
            handler_result = handler(form)
            redirect_url = redirect_url_resolver(handler_result)

            # redirect to a new URL:
            return render(
                request,
                "wirgarten/generic/modal/form-modal-redirect.html",
                {"url": redirect_url},
            )
        else:
            print("Form not valid! ", form.errors)

    # if a GET (or any other method) we'll create a blank modal
    else:
        form = (
            form_class(instance=instance, **kwargs)
            if instance
            else form_class(**kwargs)
        )

    return TemplateResponse(
        request, "wirgarten/generic/modal/form-modal-content.html", {"form": form}
    )
