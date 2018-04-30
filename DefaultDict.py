class DefaultDict(dict):
    def __init__(self, *args, default=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._default = default

    def __getitem__(self, item):
        if item in self:
            return super().__getitem__(item)

        if hasattr(self._default, "__call__"):
            return self._default.__call__(item)
        else:
            return self._default
