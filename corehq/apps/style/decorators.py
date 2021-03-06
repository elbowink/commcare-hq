from corehq import toggles


def check_preview_bootstrap3():
    def decorate(fn):
        """
        Decorator to Toggle on the use of bootstrap 3.
        """
        def wrapped(request, *args, **kwargs):
            request.preview_bootstrap3 = (
                hasattr(request, 'user')
                and toggles.BOOTSTRAP3_PREVIEW.enabled(request.user.username))
            return fn(request, *args, **kwargs)
        return wrapped
    return decorate


def use_select2():
    def decorate(fn):
        """
        Decorator to Toggle on the use of bootstrap 3.
        """
        def wrapped(request, *args, **kwargs):
            request.use_select2 = True
            return fn(request, *args, **kwargs)
        return wrapped
    return decorate


def use_knockout_js():
    def decorate(fn):
        """
        Decorator to Toggle on the use of bootstrap 3.
        """
        def wrapped(request, *args, **kwargs):
            request.use_knockout_js = True
            return fn(request, *args, **kwargs)
        return wrapped
    return decorate
