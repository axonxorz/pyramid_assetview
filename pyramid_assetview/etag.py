import os

from zope.interface import (
    implementer
    )

from interfaces import IEtagger


@implementer(IEtagger)
class BaseEtagger(object):

    def __call__(self, resource_path, cache_region, file_path, request):
        raise NotImplementedError()


class FileModTimeEtagger(BaseEtagger):

    def __call__(self, resource_path, cache_region, file_path, request):
        cache_stat = os.stat(file_path)
        return '%s-%s' % (cache_region, cache_stat.st_mtime)
