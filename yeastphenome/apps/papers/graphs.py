from yeastphenome.apps.papers.models import Paper


def get_papers_by_year():
    
    import numpy as np

    """Generate a dictionary of number of papers by year."""
    pub_dates = Paper.objects.all_valid().values_list("pub_date", flat=True)
    [years, years_counts] = np.unique(np.array(pub_dates), return_counts=True)

    counts = {years[ix]: years_counts[ix] for ix in np.arange(years.shape[0])}

    return counts
