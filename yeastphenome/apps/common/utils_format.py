def truncated_list_as_str(lst, num=10, sort=False):

    lst = [el for el in lst if not el == "" and el is not None]

    if sort:
        lst.sort()

    lst_len = len(lst)
    if lst_len == 0:
        lst_as_str = ""
    elif lst_len <= num:
        lst_as_str = "; ".join(lst)
    else:
        num_remaining = lst_len - num
        lst_as_str = "; ".join(lst[:num]) + " ... and " + str(num_remaining) + " more"

    return lst_as_str


def join_and(lst):

    lst_str = ""
    if len(lst) > 1:
        lst_str = ", ".join(lst[:-1]) + " and " + lst[-1]
    elif len(lst) == 1:
        lst_str = lst[0]

    return lst_str


def update_values_with_percentile(qs_values, key):

    import numpy as np
    from scipy.stats import rankdata

    values_arr = np.array(qs_values.values_list(key, flat=True))
    values_percentiles = 100 * rankdata(values_arr) / values_arr.shape[0]

    def update(values_dict, ix):
        values_dict["percentile"] = values_percentiles[ix]
        return values_dict

    values = [update(values_dict, ix) for ix, values_dict in enumerate(list(qs_values))]

    return values
