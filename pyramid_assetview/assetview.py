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

    def __init__(self, path_spec, get_username=None, package_name=None):
        if ':' not in path_spec and package_name is None:
            raise AssetViewConfigurationError("Must specify full package name in add_asset_view (mypackage:path) or "
                                              "provide the package_name argument")

        asset_package_name, docroot = resolve_asset_spec(path_spec)
        if asset_package_name is None:
            asset_package_name = package_name

        self.package_name = asset_package_name
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

    @staticmethod
    def guess_mime(filename):
        """Guess the mime-type of a filename, with hardcodes for JS and CSS"""
        if filename.endswith('.js'):
            return 'application/javascript'
        elif filename.endswith('.css'):
            return 'text/css'
        else:
            type, encoding = mimetypes.guess_type(filename)
            return type

    def _serve_raw(self, file_path, request):
        """Serve a raw filesystem path, no rendering possible."""
        mime_name = file_path
        if not os.path.exists(file_path):
            return HTTPNotFound(request.url)
        return FileResponse(file_path, request, content_type=self.guess_mime(mime_name))

    def _serve_maybe_rendered(self, resource_path, cache_region, request):
        """Service a package resource file, rendered if applicable, raw if otherwise."""
        render = False
        if resource_path.endswith('.mak'):
            render = True
            # Mime name, without the .mak
            mime_name = resource_path[:-4]
        else:
            mime_name = resource_path

        file_path = resource_filename(self.package_name, resource_path)
        if not render:
            return self._serve_raw(file_path, request)
        else:
            # Handle ETag & Caching
            cache_stat = os.stat(file_path)
            cache_etag = '%s-%s' % (cache_region, cache_stat.st_mtime)
            if cache_etag == str(request.if_none_match).strip('"'):
                return HTTPNotModified()

            renderpath = '%s:%s' % (self.package_name, resource_path)
            response = render_to_response(renderpath, {}, request=request)
            response.content_type = self.guess_mime(mime_name)
            response.etag = cache_etag
            return response

    def _generate(self, subpath, cache_region, request):
        render = False
        if self.package_name: # package resource
            resource_path = '%s/%s' % (self.docroot.rstrip('/'), subpath)
            if resource_path.startswith('/'):
                # Special case for absolute filenames. Used if AssetView is serving directly from a filesystem
                # path, instead of using a python package reference
                return self._serve_raw(resource_path, request)
            else:
                if resource_exists(self.package_name, resource_path + '.mak'):
                    # Support rendering for Mako templates
                    resource_path += '.mak'
                return self._serve_maybe_rendered(resource_path, cache_region, request)

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
