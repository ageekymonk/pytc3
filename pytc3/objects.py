from .base import RESTObject
from .manager import RESTManager
from .mixins import CRUDMixin
from .utils import raise_on_status


class BuildType(RESTObject):
    _managers = (
        ('builds', 'BuildManager'),
    )

class BuildTypeManager(CRUDMixin, RESTManager):
    _path = '/app/rest/projects/id:%(project_id)s/buildTypes'
    _get_path = '/app/rest/buildTypes'
    _obj_cls = BuildType

    _from_parent_attrs = {'project_id': 'id'}
    # Path to get the list from the json object
    _extract_path = ('buildType',)

    _list_filters = ('name')
    _list_sorters = ('name')

class Project(RESTObject):
    _managers = (
        ('buildtypes', 'BuildTypeManager'),
        ('builds', 'BuildManager'),
    )

class ProjectManager(CRUDMixin, RESTManager):
    _path = '/app/rest/projects'
    _get_path = '/app/rest/projects'
    _obj_cls = Project

    # Path to get the list from the json object
    _extract_path = ('project',)

    _list_filters = ('name')
    _list_sorters = ('name')

class Build(RESTObject):
    _managers = (
        ('properties', 'BuildAttributeManager'),
        ('changes', 'BuildChangeManager')
    )

class BuildManager(CRUDMixin, RESTManager):
    _path = {
        Project.__name__ : '/app/rest/builds/?locator=project(id:%(project_id)s)',
        BuildType.__name__: '/app/rest/buildTypes/id:%(buildtype_id)s/builds'
    }
    _get_path = '/app/rest/builds'
    _list_path = '/app/rest/builds'
    _obj_cls = Build

    _from_parent_attrs =  {
        BuildType.__name__: {'buildtype_id': 'id'},
        Project.__name__: {'project_id': 'id'}
    }
    # Path to get the list from the json object
    _extract_path = ('build',)

    _list_filters = ('number')
    _list_sorters = ('name')

class BuildAttributes(RESTObject):
    pass

class BuildAttributeManager(CRUDMixin, RESTManager):
    _path = '/app/rest/builds/id:%(build_id)s/attributes'
    _obj_cls = BuildAttributes

    _from_parent_attrs = {'build_id': 'id'}

    # Path to get the list from the json object
    _extract_path = ('property',)

    _list_filters = ('name')
    _list_sorters = ('name')

class BuildChanges(RESTObject):
    _managers = (
        ('repository', 'VcsRepositoryManager'),
    )

class BuildChangeManager(CRUDMixin, RESTManager):
    _path = '/app/rest/changes/?locator=build:(id:%(build_id)s)'
    _get_path = '/app/rest/changes'
    _obj_cls = BuildChanges

    _from_parent_attrs = {'build_id': 'id'}

    # Path to get the list from the json object
    _extract_path = ('change',)

    _list_filters = ('name')
    _list_sorters = ('name')

class VcsRepository(RESTObject):
    def __init__(self, manager, attrs):
        super().__init__(manager, attrs)
        properties = {}
        for elem in self._attrs['properties']['property']:
            properties[elem['name']] = elem.get('value', '')

        self.url = properties['url']
        self.branch = properties['branch']

class VcsRepositoryManager(CRUDMixin, RESTManager):
    _path = '/app/rest/changes/id:%(change_id)s/vcsRootInstance'
    _get_path = '/app/rest/vcs-root-instances'
    _obj_cls = VcsRepository

    _from_parent_attrs = {'change_id': 'id'}
    # Path to get the list from the json object
    _extract_path = ()

    _list_filters = ('name')
    _list_sorters = ('name')
