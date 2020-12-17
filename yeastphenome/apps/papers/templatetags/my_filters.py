from django import template

register = template.Library()


@register.filter(name="join_and_more", is_safe=True)
def join_and_more(qs, number_obj_to_show, delim=";"):
    with_space = "%s " % delim
    l = len(qs)
    if l == 0:
        return ""
    elif l <= number_obj_to_show:
        return with_space.join((u"%s" % obj) for obj in qs)
    else:
        number_obj_remaining = l - number_obj_to_show
        return (
            with_space.join((u"%s" % obj) for obj in qs[: number_obj_to_show - 1])
            + " ... (and "
            + str(number_obj_remaining)
            + " more)"
        ).strip()


@register.filter
def lookup(d, key):
    return d[key]


@register.filter
def range(min=5):
    return range(min)


@register.filter
def index(indexable, i):
    return indexable[i]
