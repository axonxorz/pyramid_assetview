import os

from zope.interface import (
    implementer
    )

from interfaces import IEtagger


@implementer(IEtagger)
class BaseEtagger(object):

    def __init__(self, include_cache_region=True):
        self.include_cache_region = include_cache_region

    def __call__(self, resource_path, cache_region, file_path, request):
        token = self.tokenize(resource_path, cache_region, file_path, request)
        if self.include_cache_region:
            return '{}-{}'.format(cache_region, token)
        else:
            return token

    def tokenize(self, resource_path, cache_region, file_path, request):
        raise NotImplementedError()


class FileModTimeEtagger(BaseEtagger):

    def tokenize(self, resource_path, cache_region, file_path, request):
        return str(os.stat(file_path).st_mtime)


class StaticValueEtagger(BaseEtagger):

    def __init__(self, value, include_cache_region=True):
        super(StaticValueEtagger, self).__init__(include_cache_region=include_cache_region)
        self.value = value

    def tokenize(self, resource_path, cache_region, file_path, request):
        return self.value