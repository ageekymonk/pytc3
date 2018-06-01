import os
import urllib

import requests

from .exceptions import *
from .objects import *
from .utils import parse_date_string, raise_on_status


class TeamCity(object):

    def __init__(self,
                 username=None, password=None,
                 protocol='http', server='127.0.0.1', port=None,
                 session=None, ssl_verify=True, timeout=None):


        # User's credential to login to teamcity server
        self.username = username
        self.password = password

        # Protocol to use to connect to teamcity server api. http/https
        self.protocol = protocol

        # Host name of the server
        self.server = server
        self.port = port or (443 if protocol == 'https' else 80)

        self._url = f'{self.protocol}://{self.server}:{self.port}/httpAuth'

        self.ssl_verify = ssl_verify
        self.timeout = timeout

        self.headers = {}
        self.session = session or requests.Session()
        self._set_session_auth()

        self.projects = ProjectManager(self)

    @classmethod
    def from_environ(cls):
        return TeamCity(
            protocol=os.environ.get('TEAMCITY_PROTO'),
            username=os.environ.get('TEAMCITY_USER'),
            password=os.environ.get('TEAMCITY_PASSWORD'),
            server=os.environ.get('TEAMCITY_HOST'))

    def _set_session_auth(self):
        self.session.auth = (self.username, self.password)
        self.session.headers['Accept'] = 'application/json'

    def _create_headers(self, content_type=None):
        request_headers = self.headers.copy()
        if content_type is not None:
            request_headers['Content-type'] = content_type
        return request_headers

    def _get_session_opts(self, content_type):
        return {
            'headers': self._create_headers(content_type),
            'auth': self.session.auth,
            'timeout': self.timeout,
            'verify': self.ssl_verify
        }

    def _raw_get(self, path_, content_type=None, streamed=False, **kwargs):
        if path_.startswith('http://') or path_.startswith('https://'):
            url = path_
        else:
            url = '%s%s' % (self._url, path_)

        opts = self._get_session_opts(content_type)
        try:
            return self.session.get(url, params=kwargs, stream=streamed,
                                    **opts)
        except Exception as e:
            raise TeamcityConnectionError(
                "Can't connect to Teamcity server (%s)" % e)

    def _raw_list(self, path_, cls, **kwargs):
        params = kwargs.copy()

        catch_recursion_limit = kwargs.get('safe_all', False)
        get_all_results = (kwargs.get('all', False) is True
                           or catch_recursion_limit)

        # Remove these keys to avoid breaking the listing (urls will get too
        # long otherwise)
        for key in ['all', 'next_url', 'safe_all']:
            if key in params:
                del params[key]

        r = self._raw_get(path_, **params)
        raise_error_from_response(r, TeamcityListError)

        # Add _from_api manually, because we are not creating objects
        # through normal path_
        params['_from_api'] = True

        results = [cls(self, item, **params) for item in r.json()
                   if item is not None]
        try:
            if ('next' in r.links and 'url' in r.links['next']
                    and get_all_results):
                args = kwargs.copy()
                args['next_url'] = r.links['next']['url']
                results.extend(self.list(cls, **args))
        except Exception as e:
            # Catch the recursion limit exception if the 'safe_all'
            # kwarg was provided
            if not (catch_recursion_limit and
                    "maximum recursion depth exceeded" in str(e)):
                raise e

        return results

    def list(self, obj_class, **kwargs):
        """Request the listing of Teamcity resources.

        Args:
            obj_class (object): The class of resource to request.
            **kwargs: Additional arguments to send to Teamcity.

        Returns:
            list(obj_class): A list of objects of class `obj_class`.

        Raises:
            TeamcityConnectionError: If the server cannot be reached.
            TeamcityListError: If the server fails to perform the request.
        """
        missing = []
        for k in itertools.chain(obj_class.requiredUrlAttrs,
                                 obj_class.requiredListAttrs):
            if k not in kwargs:
                missing.append(k)
        if missing:
            raise TeamcityListError('Missing attribute(s): %s' %
                                  ", ".join(missing))

        url = self._construct_url(id_=None, obj=obj_class, parameters=kwargs)

        return self._raw_list(url, obj_class, **kwargs)

    def get(self, obj_class, id=None, **kwargs):
        """Request a Teamcity resources.

        Args:
            obj_class (object): The class of resource to request.
            id: The object ID.
            **kwargs: Additional arguments to send to Teamcity.

        Returns:
            obj_class: An object of class `obj_class`.

        Raises:
            TeamcityConnectionError: If the server cannot be reached.
            TeamcityGetError: If the server fails to perform the request.
        """
        missing = []
        for k in itertools.chain(obj_class.requiredUrlAttrs,
                                 obj_class.requiredGetAttrs):
            if k not in kwargs:
                missing.append(k)
        if missing:
            raise TeamcityGetError('Missing attribute(s): %s' %
                                 ", ".join(missing))

        url = self._construct_url(id_=_sanitize(id), obj=obj_class,
                                  parameters=kwargs)

        r = self._raw_get(url, **kwargs)
        raise_error_from_response(r, TeamcityGetError)
        return r.json()

    def relative_url(self, uri):
        return '%s/%s' % (self.base_url, uri)


    def plugins(self):
        url = self.base_url + '/app/rest/server/plugins'
        res = self.session.get(url)
        raise_on_status(res)
        data = res.json()
        plugins = []
        for plugin in data['plugin']:
            plugins.append(
                Plugin(name=plugin.get('name'),
                       display_name=plugin.get('displayName'),
                       version=plugin.get('version'),
                       load_path=plugin.get('loadPath'))
            )
        return plugins

    @property
    def server_info(self):
        url = self.base_url + '/app/rest/server'
        res = self.session.get(url)
        raise_on_status(res)

        data = res.json()
        return TeamCityServerInfo(
            version=data['version'],
            version_major=data['versionMajor'],
            version_minor=data['versionMinor'],
            build_number=data['buildNumber'],
            start_time_str=data['startTime'],
            current_time_str=data['currentTime'],
            build_date_str=data['buildDate'],
            internal_id=data['internalId'],
            web_url=data['webUrl'])

    def _build_url(self, path):
        """Returns the full url from path.

        If path is already a url, return it unchanged. If it's a path, append
        it to the stored url.

        This is a low-level method, different from _construct_url _build_url
        have no knowledge of TeamcityObject's.

        Returns:
            str: The full URL
        """
        if path.startswith('http://') or path.startswith('https://'):
            return path
        else:
            return '%s%s' % (self._url, path)

    def http_request(self, verb, path, query_data={}, post_data={},
                     streamed=False, files=None, **kwargs):
        """Make an HTTP request to the Teamcity server.

        Args:
            verb (str): The HTTP method to call ('get', 'post', 'put',
                        'delete')
            path (str): Path or full URL to query ('/projects' or
                        'http://whatever/v4/api/projecs')
            query_data (dict): Data to send as query parameters
            post_data (dict): Data to send in the body (will be converted to
                              json)
            streamed (bool): Whether the data should be streamed
            **kwargs: Extra data to make the query (e.g. sudo, per_page, page)

        Returns:
            A requests result object.

        Raises:
            TeamcityHttpError: When the return code is not 2xx
        """

        def sanitized_url(url):
            parsed = urllib.parse.urlparse(url)
            new_path = parsed.path.replace('.', '%2E')
            return parsed._replace(path=new_path).geturl()

        url = self._build_url(path)

        def copy_dict(dest, src):
            for k, v in src.items():
                if isinstance(v, dict):
                    # Transform dict values in new attributes. For example:
                    # custom_attributes: {'foo', 'bar'} =>
                    #   custom_attributes['foo']: 'bar'
                    for dict_k, dict_v in v.items():
                        dest['%s[%s]' % (k, dict_k)] = dict_v
                else:
                    dest[k] = v

        params = {}
        copy_dict(params, query_data)
        copy_dict(params, kwargs)

        opts = self._get_session_opts(content_type='application/json')

        # don't set the content-type header when uploading files
        if files is not None:
            del opts["headers"]["Content-type"]

        verify = opts.pop('verify')
        timeout = opts.pop('timeout')

        # Requests assumes that `.` should not be encoded as %2E and will make
        # changes to urls using this encoding. Using a prepped request we can
        # get the desired behavior.
        # The Requests behavior is right but it seems that web servers don't
        # always agree with this decision (this is the case with a default
        # teamcity installation)
        req = requests.Request(verb, url, json=post_data, params=params,
                               files=files, **opts)
        prepped = self.session.prepare_request(req)
        prepped.url = sanitized_url(prepped.url)
        settings = self.session.merge_environment_settings(
            prepped.url, {}, streamed, verify, None)

        # obey the rate limit by default
        obey_rate_limit = kwargs.get("obey_rate_limit", True)

        while True:
            result = self.session.send(prepped, timeout=timeout, **settings)

            if 200 <= result.status_code < 300:
                return result

            if 429 == result.status_code and obey_rate_limit:
                wait_time = int(result.headers["Retry-After"])
                time.sleep(wait_time)
                continue

            try:
                error_message = result.json()['message']
            except (KeyError, ValueError, TypeError):
                error_message = result.content

            if result.status_code == 401:
                raise TeamcityAuthenticationError(
                    response_code=result.status_code,
                    error_message=error_message,
                    response_body=result.content)

            raise TeamcityHttpError(response_code=result.status_code,
                                  error_message=error_message,
                                  response_body=result.content)

    def http_get(self, path, query_data={}, streamed=False, **kwargs):
        """Make a GET request to the Teamcity server.

        Args:
            path (str): Path or full URL to query ('/projects' or
                        'http://whatever/v4/api/projecs')
            query_data (dict): Data to send as query parameters
            streamed (bool): Whether the data should be streamed
            **kwargs: Extra data to make the query (e.g. sudo, per_page, page)

        Returns:
            A requests result object is streamed is True or the content type is
            not json.
            The parsed json data otherwise.

        Raises:
            TeamcityHttpError: When the return code is not 2xx
            TeamcityParsingError: If the json data could not be parsed
        """
        result = self.http_request('get', path, query_data=query_data,
                                   streamed=streamed, **kwargs)
        if (result.headers['Content-Type'] == 'application/json' and
           not streamed):
            try:
                return result.json()
            except Exception:
                raise TeamcityParsingError(
                    error_message="Failed to parse the server message")
        else:
            return result

    def http_list(self, path, query_data={}, as_list=None, **kwargs):
        """Make a GET request to the Teamcity server for list-oriented queries.

        Args:
            path (str): Path or full URL to query ('/projects' or
                        'http://whatever/v4/api/projecs')
            query_data (dict): Data to send as query parameters
            **kwargs: Extra data to make the query (e.g. sudo, per_page, page,
                      all)

        Returns:
            list: A list of the objects returned by the server. If `as_list` is
            False and no pagination-related arguments (`page`, `per_page`,
            `all`) are defined then a TeamcityList object (generator) is returned
            instead. This object will make API calls when needed to fetch the
            next items from the server.

        Raises:
            TeamcityHttpError: When the return code is not 2xx
            TeamcityParsingError: If the json data could not be parsed
        """

        # In case we want to change the default behavior at some point
        as_list = True if as_list is None else as_list

        get_all = kwargs.get('all', False)
        url = self._build_url(path)

        return self.http_request('get', url, query_data, **kwargs).json()

class TeamCityServerInfo(object):
    def __init__(self,
                 version, version_major, version_minor, build_number,
                 start_time_str, current_time_str, build_date_str,
                 internal_id, web_url):
        self.version = version
        self.version_major = version_major
        self.version_minor = version_minor
        self.build_number = build_number
        self.start_time_str = start_time_str
        self.current_time_str = current_time_str
        self.build_date_str = build_date_str
        self.internal_id = internal_id
        self.web_url = web_url

    def __repr__(self):
        return '<%s.%s: web_url=%r version=%r>' % (
            self.__module__,
            self.__class__.__name__,
            self.web_url,
            self.version)

    @property
    def start_time(self):
        return parse_date_string(self.start_time_str)

    @property
    def current_time(self):
        return parse_date_string(self.current_time_str)

    @property
    def build_date(self):
        return parse_date_string(self.build_date_str)
