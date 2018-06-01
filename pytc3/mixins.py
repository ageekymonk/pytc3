from . import base
from . import exceptions as exc


class GetMixin(object):
    @exc.on_http_error(exc.TeamcityGetError)
    def get(self, id, lazy=False, **kwargs):
        """Retrieve a single object.

        Args:
            id (int or str): ID of the object to retrieve
            lazy (bool): If True, don't request the server, but create a
                         shallow object giving access to the managers. This is
                         useful if you want to avoid useless calls to the API.
            **kwargs: Extra options to send to the Teamcity server (e.g. sudo)

        Returns:
            object: The generated RESTObject.

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcityGetError: If the server cannot perform the request
        """
        if not isinstance(id, int):
            id = id.replace('/', '%2F')

        path = '%s/id:%s' % (self.get_path, id)
        if lazy is True:
            return self._obj_cls(self, {self._obj_cls._id_attr: id})
        server_data = self.teamcity.http_get(path, **kwargs)
        return self._obj_cls(self, server_data)


class GetWithoutIdMixin(object):
    @exc.on_http_error(exc.TeamcityGetError)
    def get(self, id=None, **kwargs):
        """Retrieve a single object.

        Args:
            **kwargs: Extra options to send to the Teamcity server (e.g. sudo)

        Returns:
            object: The generated RESTObject

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcityGetError: If the server cannot perform the request
        """
        server_data = self.teamcity.http_get(self.path, **kwargs)
        return self._obj_cls(self, server_data)


class RefreshMixin(object):
    @exc.on_http_error(exc.TeamcityGetError)
    def refresh(self, **kwargs):
        """Refresh a single object from server.

        Args:
            **kwargs: Extra options to send to the Teamcity server (e.g. sudo)

        Returns None (updates the object)

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcityGetError: If the server cannot perform the request
        """
        path = '%s/%s' % (self.manager.path, self.id)
        server_data = self.manager.teamcity.http_get(path, **kwargs)
        self._update_attrs(server_data)


class ListMixin(object):
    @exc.on_http_error(exc.TeamcityListError)
    def list(self, **kwargs):
        """Retrieve a list of objects.

        Args:
            all (bool): If True, return all the items, without pagination
            per_page (int): Number of items to retrieve per request
            page (int): ID of the page to return (starts with page 1)
            as_list (bool): If set to False and no pagination option is
                defined, return a generator instead of a list
            **kwargs: Extra options to send to the Teamcity server (e.g. sudo)

        Returns:
            list: The list of objects, or a generator if `as_list` is False

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcityListError: If the server cannot perform the request
        """

        # Duplicate data to avoid messing with what the user sent us
        data = kwargs.copy()

        # We get the attributes that need some special transformation
        # TODO: Do we need this?
        # types = getattr(self, '_types', {})
        # if types:
        #     for attr_name, type_cls in types.items():
        #         if attr_name in data.keys():
        #             type_obj = type_cls(data[attr_name])
        #             data[attr_name] = type_obj.get_for_api()

        # Allow to overwrite the path, handy for custom listings
        path = data.pop('path', self.path)

        obj = self.teamcity.http_list(path, **data)

        for elem in self._extract_path:
            obj=obj.get(elem, [])

        if isinstance(obj, list):
            return [self.get(item['id']) for item in obj]
        else:
            return [ self.get(obj['id']) ]

class GetFromListMixin(ListMixin):
    def get(self, id, **kwargs):
        """Retrieve a single object.

        Args:
            id (int or str): ID of the object to retrieve
            **kwargs: Extra options to send to the Teamcity server (e.g. sudo)

        Returns:
            object: The generated RESTObject

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcityGetError: If the server cannot perform the request
        """
        try:
            gen = self.list()
        except exc.TeamcityListError:
            raise exc.TeamcityGetError(response_code=404,
                                     error_message="Not found")

        for obj in gen:
            if str(obj.get_id()) == str(id):
                return obj

        raise exc.TeamcityGetError(response_code=404, error_message="Not found")


class FilterMixin(object):
    @exc.on_http_error(exc.TeamcityListError)
    def filter_by(self, **kwargs):
        data = kwargs.copy()
        path = data.pop('path', self.path)
        print(self.path)
        if '?locator=' in path:
            path = path + ','
            for k,v in data.items():
                path = path + f'{k}:{v}'
        else:
            path = path + '/?locator='
            for k,v in data.items():
                path = path + f'{k}:{v}'

        obj = self.teamcity.http_list(path)
        for elem in self._extract_path:
            obj=obj.get(elem, [])

        if isinstance(obj, list):
            return [self.get(item['id']) for item in obj]
        else:
            return TeamcityError('Unexpected object {obj}')


class RetrieveMixin(ListMixin, GetMixin, FilterMixin):
    pass


class CreateMixin(object):
    def _check_missing_create_attrs(self, data):
        required, optional = self.get_create_attrs()
        missing = []
        for attr in required:
            if attr not in data:
                missing.append(attr)
                continue
        if missing:
            raise AttributeError("Missing attributes: %s" % ", ".join(missing))

    def get_create_attrs(self):
        """Return the required and optional arguments.

        Returns:
            tuple: 2 items: list of required arguments and list of optional
                   arguments for creation (in that order)
        """
        return getattr(self, '_create_attrs', (tuple(), tuple()))

    @exc.on_http_error(exc.TeamcityCreateError)
    def create(self, data, **kwargs):
        """Create a new object.

        Args:
            data (dict): parameters to send to the server to create the
                         resource
            **kwargs: Extra options to send to the Teamcity server (e.g. sudo)

        Returns:
            RESTObject: a new instance of the managed object class built with
                the data sent by the server

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcityCreateError: If the server cannot perform the request
        """
        self._check_missing_create_attrs(data)

        # We get the attributes that need some special transformation
        types = getattr(self, '_types', {})

        if types:
            # Duplicate data to avoid messing with what the user sent us
            data = data.copy()
            for attr_name, type_cls in types.items():
                if attr_name in data.keys():
                    type_obj = type_cls(data[attr_name])
                    data[attr_name] = type_obj.get_for_api()

        # Handle specific URL for creation
        path = kwargs.pop('path', self.path)
        server_data = self.teamcity.http_post(path, post_data=data, **kwargs)
        return self._obj_cls(self, server_data)


class UpdateMixin(object):
    def _check_missing_update_attrs(self, data):
        required, optional = self.get_update_attrs()
        missing = []
        for attr in required:
            if attr not in data:
                missing.append(attr)
                continue
        if missing:
            raise AttributeError("Missing attributes: %s" % ", ".join(missing))

    def get_update_attrs(self):
        """Return the required and optional arguments.

        Returns:
            tuple: 2 items: list of required arguments and list of optional
                   arguments for update (in that order)
        """
        return getattr(self, '_update_attrs', (tuple(), tuple()))

    @exc.on_http_error(exc.TeamcityUpdateError)
    def update(self, id=None, new_data={}, **kwargs):
        """Update an object on the server.

        Args:
            id: ID of the object to update (can be None if not required)
            new_data: the update data for the object
            **kwargs: Extra options to send to the Teamcity server (e.g. sudo)

        Returns:
            dict: The new object data (*not* a RESTObject)

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcityUpdateError: If the server cannot perform the request
        """

        if id is None:
            path = self.path
        else:
            path = '%s/%s' % (self.path, id)

        self._check_missing_update_attrs(new_data)

        # We get the attributes that need some special transformation
        types = getattr(self, '_types', {})
        for attr_name, type_cls in types.items():
            if attr_name in new_data.keys():
                type_obj = type_cls(new_data[attr_name])
                new_data[attr_name] = type_obj.get_for_api()

        return self.teamcity.http_put(path, post_data=new_data, **kwargs)


class SetMixin(object):
    @exc.on_http_error(exc.TeamcitySetError)
    def set(self, key, value, **kwargs):
        """Create or update the object.

        Args:
            key (str): The key of the object to create/update
            value (str): The value to set for the object
            **kwargs: Extra options to send to the server (e.g. sudo)

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcitySetError: If an error occured

        Returns:
            obj: The created/updated attribute
        """
        path = '%s/%s' % (self.path, key.replace('/', '%2F'))
        data = {'value': value}
        server_data = self.teamcity.http_put(path, post_data=data, **kwargs)
        return self._obj_cls(self, server_data)


class DeleteMixin(object):
    @exc.on_http_error(exc.TeamcityDeleteError)
    def delete(self, id, **kwargs):
        """Delete an object on the server.

        Args:
            id: ID of the object to delete
            **kwargs: Extra options to send to the Teamcity server (e.g. sudo)

        Raises:
            TeamcityAuthenticationError: If authentication is not correct
            TeamcityDeleteError: If the server cannot perform the request
        """
        if not isinstance(id, int):
            id = id.replace('/', '%2F')
        path = '%s/%s' % (self.path, id)
        self.teamcity.http_delete(path, **kwargs)

class CRUDMixin(GetMixin, ListMixin, FilterMixin, CreateMixin, UpdateMixin, DeleteMixin):
    pass
