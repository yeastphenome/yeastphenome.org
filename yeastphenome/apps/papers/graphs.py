from django.db.models import Count
from yeastphenome.apps.papers.models import Paper
import collections


def get_papers_by_year(add_padding=True):
    """Generate a dictionary of number of papers by year. If add_padding is True,
    add an empty year to the left and right (default)
    """
    counts = (
        Paper.objects.all_valid().values("pub_date").order_by()
        .annotate(the_count=Count("pub_date"))
    )
    counts = {x["pub_date"]: x["the_count"] for x in counts.order_by("pub_date") if x["pub_date"] != 0}

    # # Add padding on left and right for one year
    # if add_padding:
    #     min_year = min(counts.keys())
    #     max_year = max(counts.keys())
    #     counts[min_year - 1] = 0
    #     counts[max_year + 1] = 0
    return counts
