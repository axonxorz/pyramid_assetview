import os
import mimetypes
from os.path import normcase, normpath, join, exists
import hashlib

from pkg_resources import resource_exists, resource_filename
from repoze.lru import lru_cache

from pyramid.httpexceptions import HTTPNotFound, HTTPNotModified

from pyramid.events import NewRequest
from pyramid.response import FileResponse
from pyramid.renderers import render_to_response
from pyramid.asset import resolve_asset_spec
from pyramid.path import caller_package

class AssetViewCacheError(Exception): pass

class AssetViewConfigurationError(Exception): pass

class AssetView(object):
    """Similar to pyramid's static_view class. Resolves an asset,
    searching for filename variations that would resolve to a template.
    If not found, the file is directly served. If a template extension
    is found, it is rendered then served"""

    def __init__(self, path_spec, get_username=None):
        if ':' not in path_spec:
            raise AssetViewConfigurationError("Must specify full package name in add_asset_view (mypackage:path)")

        package_name, docroot = resolve_asset_spec(path_spec)
        self.package_name = package_name
        self.docroot = docroot
        self.norm_docroot = normcase(normpath(docroot))
        if get_username is not None:
            self._get_username = get_username

    def _get_username(self, request):
        raise NotImplementedError("Must supply a callable to __init__'s get_username argument")

    def _get_cache_key(self, request):
        region = request.matchdict['cache_region']

        subpath = request.matchdict['subpath']
        query_string = request.query_string

        cache_key = '%s%s%s' % (self.package_name, subpath, query_string)
        cache_key = hashlib.md5(cache_key).hexdigest()

        if region == 'global':
            return 'cache:global:%s' % cache_key
        elif region == 'user':
            username = self._get_username(request)
            if username is None:
                username = '__guest'
            return 'cache:user:%s:%s' % (username, cache_key)
        else:
            raise AssetViewCacheError("Unconfigured cache region: %s" % (region))

    def __call__(self, context, request):
        cache_region = request.matchdict['cache_region']

        subpath = request.matchdict['subpath']
        subpath = _secure_path(request.matchdict['subpath'])

        #cache_key = self._get_cache_key(request)

        if subpath is None:
            return HTTPNotFound('Out of bounds: %s' % subpath)

        return self._generate(subpath, cache_region, request)

    def _generate(self, subpath, cache_region, request):
        render = False
        if self.package_name: # package resource
            resource_path = '%s/%s' % (self.docroot.rstrip('/'), subpath)
            if resource_exists(self.package_name, resource_path + '.mak'):
                resource_path += '.mak'

            filepath = resource_filename(self.package_name, resource_path)
            if not resource_exists(self.package_name, resource_path):
                return HTTPNotFound(request.url)
        else:
            raise NotImplementedError("Cannot serve raw filesystem files, must be part of a python package")

        if resource_path.endswith('.mak'):
            render = True

        if not render:
            return FileResponse(filepath, request)
        else:
            # Handle ETag
            cache_stat = os.stat(filepath)

            cache_etag = '%s-%s' % (cache_region, cache_stat.st_mtime)
            if cache_etag == str(request.if_none_match).strip('"'):
                return HTTPNotModified()

            renderpath = '%s:%s' % (self.package_name, resource_path)
            response = render_to_response(renderpath, {}, request=request)
            response.content_type, response.content_encoding = mimetypes.guess_type(filepath, strict=False)
            response.etag = cache_etag
            return response

slash = '/'

_seps = set(['/', os.sep])
def _contains_slash(item):
    for sep in _seps:
        if sep in item:
            return True

_has_insecure_pathelement = set(['..', '.', '']).intersection

@lru_cache(1000)
def _secure_path(path_tuple):
    if _has_insecure_pathelement(path_tuple):
        # belt-and-suspenders security; this should never be true
        return None
    if any([_contains_slash(item) for item in path_tuple]):
        return None
    encoded = slash.join(path_tuple) # will be unicode
    return encoded
