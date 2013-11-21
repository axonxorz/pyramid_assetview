from zope.interface import (
    Attribute,
    Interface
    )

class IAssetURLInfo(Interface):
    """A policy for generating URLs to assets governed by AssetViews"""
    def add(config, asset_spec, path_spec, **extra):
        """Add a new asset info registration"""

    def generate(asset_spec, path, cache_region, request, **kw):
        """Generate a URL for the given path"""
