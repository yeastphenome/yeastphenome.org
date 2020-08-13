from django.shortcuts import render

from ratelimit.decorators import ratelimit
from yeastphenome.apps.common.utils import get_papers_by_year
from yeastphenome.settings import (
    VIEW_RATE_LIMIT as rl_rate,
    VIEW_RATE_LIMIT_BLOCK as rl_block,
)

# Visuals


@ratelimit(key="ip", rate=rl_rate, block=rl_block)
def papers_by_year(request):
    """Render a chart.js visualization for papers by year. Color by year"""
    context = {"paper_counts": get_papers_by_year()}
    return render(request, "graphs/papers-by-year-wrapper.html", context)
