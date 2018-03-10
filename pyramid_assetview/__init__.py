from types import MethodType
import urlparse

from zope.interface import (
    Interface,
    implementer
    )

from pyramid.events import NewRequest
from pyramid.threadlocal import get_current_registry

from .interfaces import IAssetURLInfo
from .assetview import AssetView

urljoin = urlparse.urljoin
url_parse = urlparse.urlparse

def add_asset_view(config, asset_spec, path_spec, **extras):
    info = config.registry.queryUtility(IAssetURLInfo)
    if info is None:
        info = AssetURLInfo()
        config.registry.registerUtility(info, IAssetURLInfo)
    info.add(config, asset_spec, path_spec, **extras)

@implementer(IAssetURLInfo)
class AssetURLInfo(object):

    def _get_registrations(self, registry):
        try:
            reg = registry._asset_url_registrations
        except AttributeError:
            reg = registry._asset_url_registrations = []
        return reg

    def generate_url(self, asset_spec, path, cache_region, request, **kw):
        try:
            registry = request.registry
        except AttributeError: # b/w compat (for tests)
            registry = get_current_registry()

        for (reg_asset_spec, route_name, view) in self._get_registrations(registry):
            if asset_spec == reg_asset_spec:
                return request.route_url(route_name, cache_region=cache_region, subpath=path, **kw)

        raise ValueError('No asset URL definition matching %s:%s' % (asset_spec, path))

    def get_path(self, asset_spec, path, request, **kw):
        try:
            registry = request.registry
        except AttributeError: # b/w compat (for tests)
            registry = get_current_registry()

        for (reg_asset_spec, route_name, view) in self._get_registrations(registry):
            if asset_spec == reg_asset_spec:
                return view.get_path(subpath=path, request=request, **kw)

        raise ValueError('No asset URL definition matching %s:%s' % (asset_spec, path))

    def add(self, config, asset_spec, path_spec, **extras):
        route_name = '__assets_%s ' % asset_spec
        pattern = '/__assets/%s/{cache_region}/*subpath' % (asset_spec)

        # Hardcoded for now
        if extras.pop('permission', None) is not None:
            raise Exception("'permission' kwarg is not supported by add_asset_view()")
        if extras.pop('context', None) is not None:
            raise Exception("'context' kwarg is not supported by add_asset_view()")
        if extras.pop('renderer', None) is not None:
            raise Exception("'renderer' kwarg is not supported by add_asset_view()")
        if extras.pop('attr', None) is not None:
            raise Exception("'attr' kwarg is not supported by add_asset_view()")

        get_username = extras.pop('get_username', None)
        package_name = extras.pop('package_name', None)
        assetview = AssetView(path_spec, package_name=package_name, get_username=get_username)

        config.add_route(route_name, pattern, **extras)
        config.add_view(route_name=route_name,
                        view=assetview)

        def register():
            registrations = self._get_registrations(config.registry)
            registrations.append((asset_spec, route_name, assetview))

        config.action(None, callable=register)

def request_asset_url(self, asset_spec, path, cache_region='global', **kw):
    try:
        reg = self.registry
    except AttributeError:
        reg = get_current_registry()

    info = reg.queryUtility(IAssetURLInfo)
    if info is None:
        raise ValueError('No AssetURLInfo instance registered. No calls to config.add_asset_view() have been made')

    return info.generate_url(asset_spec, path, cache_region, self, **kw)

def request_asset_path(self, asset_spec, path, **kw):
    try:
        reg = self.registry
    except AttributeError:
        reg = get_current_registry()

    info = reg.queryUtility(IAssetURLInfo)
    if info is None:
        raise ValueError('No AssetURLInfo instance registered. No calls to config.add_asset_view() have been made')

    return info.get_path(asset_spec, path, self, **kw)

def add_asset_url_callables(event):
    event.request.asset_url = MethodType(request_asset_url, event.request)
    event.request.asset_path = MethodType(request_asset_path, event.request)

def includeme(config):
    config.add_directive('add_asset_view', add_asset_view)
    config.add_subscriber(add_asset_url_callables, NewRequest)
