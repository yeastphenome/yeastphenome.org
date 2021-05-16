def truncated_list_as_str(lst, num=20):
    lst_len = len(lst)
    if lst_len == 0:
        lst_as_str = ""
    elif lst_len <= num:
        lst_as_str = "; ".join(lst)
    else:
        num_remaining = lst_len - num
        lst_as_str = (
                "; ".join(lst[:num])
                + "... and "
                + str(num_remaining)
                + " more"
        )
    return lst_as_str
