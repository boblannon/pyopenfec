import json
import os
import time
import logging

import requests
import six

if six.PY2:
    from exceptions import Exception


API_KEY = os.environ.get('OPENFEC_API_KEY', None)
BASE_URL = 'https://api.open.fec.gov'
VERSION = '/v1'


class PyOpenFecException(Exception):
    """
    An exception from the PyOpenFec API.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    def __unicode__(self):
        return unicode(self.value)

    def __repr__(self):
        return repr(self.value)


class PyOpenFecApiClass(object):
    """
    Universal class for PyOpenFec API classes to inherit from.
    """
    ratelimit_remaining = 1000
    wait_time = 0.5

    def to_dict(self):
        return self.__dict__

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def count(cls, **kwargs):
        resource = '{class_name}s'.format(class_name=cls.__name__.lower())
        initial_results = cls._make_request(resource, **kwargs)
        if initial_results.get('pagination', None):
            return initial_results['pagination']['count']

    @classmethod
    def fetch(cls, **kwargs):
        if 'resource' in kwargs:
            resource = kwargs.pop('resource')
        else:
            resource = '%ss' % cls.__name__.lower()
        initial_results = cls._make_request(resource, **kwargs)

        if initial_results.get('results', None):
            if len(initial_results['results']) > 0:
                for result in initial_results['results']:
                    yield cls(**result)

        if initial_results.get('pagination', None):
            if initial_results['pagination'].get('pages', None):
                if initial_results['pagination']['pages'] > 1:
                    current_page = 2

                    while current_page <= initial_results['pagination']['pages']:
                        params = dict(kwargs)
                        params['page'] = current_page
                        paged_results = cls._make_request(resource, **params)

                        if paged_results.get('results', None):
                            if len(paged_results['results']) > 0:
                                for result in paged_results['results']:
                                    yield cls(**result)

                        current_page += 1

    @classmethod
    def _throttled_request(cls, url, params):

        if cls.ratelimit_remaining == 0:
            while cls.ratelimit_remaining == 0:
                cls.wait_time = cls.wait_time * 1.5
                logging.warn(
                    'Rate limit was about to be exceeded. Waiting {}s.'.format(
                        cls.wait_time))
                time.sleep(cls.wait_time)
                response = requests.get(url, params=params)
                cls.ratelimit_remaining = int(response.headers['x-ratelimit-remaining'])
        else:
            response = requests.get(url, params=params)
            cls.ratelimit_remaining = int(response.headers['x-ratelimit-remaining'])

        cls.wait_time = 0.5

        return response

    @classmethod
    def _make_request(cls, resource, **kwargs):
        url = BASE_URL + VERSION + '/%s' % resource

        if not API_KEY:
            raise PyOpenFecException('Please export an env var OPENFEC_API_KEY with your API key.')

        params = dict(kwargs)
        params['api_key'] = API_KEY

        r = cls._throttled_request(url, params)
        logging.debug(r.url)

        if r.status_code != 200:
            raise PyOpenFecException('OpenFEC site returned a status code of %s for this request.' % r.status_code)

        return r.json()
