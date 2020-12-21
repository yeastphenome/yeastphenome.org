from django.db.models import Count
from .models import Paper
import collections


def get_papers_by_year(add_padding=True):
    """Generate a dictionary of papers by year. If add_padding is True,
    add an empty year to the left and right (default)
    """
    counts = (
        Paper.objects.values("pub_date")
        .exclude(latest_data_status__status__name="not relevant")
        .order_by("pub_date")
        .annotate(the_count=Count("pub_date"))
    )
    counts = {x["pub_date"]: x["the_count"] for x in counts if x["pub_date"] != 0}

    # Add padding on left and right for one year
    if add_padding:
        min_year = min(counts.keys())
        max_year = max(counts.keys())
        counts[min_year - 1] = 0
        counts[max_year + 1] = 0
    return collections.OrderedDict(sorted(counts.items()))
