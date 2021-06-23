from django import template
from django.utils.safestring import mark_safe

from yeastphenome.settings import DOWNLOAD_CART_LIMIT

register = template.Library()


@register.simple_tag(name="download_button", takes_context=True)
def download_button(context, dataset_id):

    request = context["request"]

    if "cart" in request.session:
        datasets_in_cart = request.session["cart"]
    else:
        datasets_in_cart = []

    button_template = '<a id="dataset-cart-%s" role="button" class="btn %s %s download_button" data-id="%s">%s</a>'
    button_status = ""

    if not datasets_in_cart or dataset_id not in datasets_in_cart:
        button_class = "btn-primary add-to-cart"
        button_label = '<i class="bi bi-download"></i>&nbsp; Add'

        if len(datasets_in_cart) >= DOWNLOAD_CART_LIMIT:
            button_status = "disabled"

    else:
        button_class = "btn-danger remove-from-cart"
        button_label = '<i class="bi bi-download"></i>&nbsp; Remove'

    button = button_template % (
        str(dataset_id),
        button_class,
        button_status,
        str(dataset_id),
        button_label,
    )

    return mark_safe(button)
