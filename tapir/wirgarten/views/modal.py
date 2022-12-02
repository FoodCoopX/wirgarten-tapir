from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def get_form_modal(
    request, form, handler, redirect_url_resolver=(lambda x: None), **kwargs
):
    # if this is a POST request we need to process the modal data
    if request.method == "POST":
        # create a modal instance and populate it with data from the request:
        form = form(request.POST, **kwargs)
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

    # if a GET (or any other method) we'll create a blank modal
    else:
        form = form(**kwargs)

    return render(
        request, "wirgarten/generic/modal/form-modal-content.html", {"form": form}
    )
