from yeastphenome import settings


def check_space_in_cart(request, datasets):
    """The browser can only serialize 4096 bytes of cookies, so we cannot allow
    the cart to exceed this number. We have some wiggle room because the session
    is compressed, so we calculated 500 datasets (the list of ids) can go right
    up to the limit. If other session data is added, this would need to be
    decreased. Returns False if the cart cannot be added to, True otherwise
    """
    datasets_in_cart = len(request.session["cart"])
    if datasets_in_cart + len(datasets) > settings.DOWNLOAD_CART_LIMIT:
        return False
    return True
