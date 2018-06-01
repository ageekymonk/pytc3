class Manager(object):
    def __init__(self, teamcity, query_set_factory):
        self.teamcity = teamcity
        self.query_set_factory = query_set_factory

    def all(self):
        return self.query_set_factory(teamcity=self.teamcity)

class RESTManager(object):
    """Base class for CRUD operations on objects.

    Derivated class must define ``_path`` and ``_obj_cls``.

    ``_path``: Base URL path on which requests will be sent (e.g. '/app/rest/builds')
    ``_obj_cls``: The class of objects that will be created
    """
    _path = None
    _get_path = None
    _obj_cls = None
    def __init__(self, tc, parent=None):
        """REST manager constructor.

        Args:
            tc (Teamcity): TODO: fix this
            parent: REST object to which the manager is attached.
        """
        self.teamcity = tc
        cls = self.__class__
        parentcls = parent.__class__.__name__
        self._path = cls._path.get(parentcls, cls._path) if type(cls._path) is dict else cls._path
        if hasattr(cls, '_from_parent_attrs'):
            self._from_parent_attrs = cls._from_parent_attrs.get(parentcls, cls._from_parent_attrs)
        self._parent = parent  # for nested managers
        self._computed_path = self._compute_path()

    def _compute_path(self, path=None):
        self._parent_attrs = {}
        if path is None:
            path = self._path

        print(path)
        if self._parent is None or not hasattr(self, '_from_parent_attrs'):
            return path

        data = {self_attr: getattr(self._parent, parent_attr, None)
                for self_attr, parent_attr in self._from_parent_attrs.items()}
        self._parent_attrs = data
        return path % data

    @property
    def parent_attrs(self):
        return self._parent_attrs

    @property
    def path(self):
        return self._computed_path

    @property
    def get_path(self):
        return self._compute_path(self._get_path)
