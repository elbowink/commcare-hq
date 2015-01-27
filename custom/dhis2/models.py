# from django.db import models
from datetime import date
from corehq.apps.fixtures.models import FixtureDataItem, FixtureDataType, FieldList, FixtureItemField
from django.conf import settings
import requests


# TODO: Move to init
DOMAIN = 'wv-lanka'
LOOKUP_TABLE = 'dhis2_org_unit'


class JsonApiError(Exception):
    """
    JsonApiError is raised for HTTP or socket errors.
    """
    pass


class Dhis2ApiQueryError(JsonApiError):
    """
    Dhis2ApiQueryError is raised when the API returns an unexpected response.
    """
    pass


class Dhis2ConfigurationError(Exception):
    pass


class JsonApiRequest(object):
    """
    Wrap requests with URL, header and authentication for DHIS2 API
    """

    def __init__(self, host, username, password):
        self.baseurl = host + '/api/'
        self.headers = {'Accept': 'application/json'}
        self.auth = (username, password)

    @staticmethod
    def json_or_error(response):
        """
        Return HTTP status, JSON

        :raises JsonApiError: if HTTP status is not in the 200 (OK) range
        """
        if 200 <= response.status_code < 300:
            return response.status_code, response.json()
        elif response.status_code == 404:
            raise JsonApiError('API request to %s failed with HTTP status %s' %
                               (response.url, response.status_code))
        else:
            raise JsonApiError('API request to %s failed with HTTP status %s: %s' %
                               (response.url, response.status_code, response.text))

    def get(self, path, **kwargs):
        try:
            response = requests.get(self.baseurl + path, headers=self.headers, auth=self.auth, **kwargs)
        except requests.RequestException as err:
            raise JsonApiError(str(err))
        return JsonApiRequest.json_or_error(response)

    def post(self, path, data, **kwargs):
        try:
            response = requests.post(self.baseurl + path, data, headers=self.headers, auth=self.auth, **kwargs)
        except requests.RequestException as err:
            raise JsonApiError(str(err))
        return JsonApiRequest.json_or_error(response)

    def put(self, path, data, **kwargs):
        try:
            response = requests.put(self.baseurl + path, data, headers=self.headers, auth=self.auth, **kwargs)
        except requests.RequestException as err:
            raise JsonApiError(str(err))
        return JsonApiRequest.json_or_error(response)


class Dhis2Api(object):

    def __init__(self, host, username, password):
        self._username = username  # Used when creating DHIS2 events from CCHQ form data
        self._request = JsonApiRequest(host, username, password)
        self._tracked_entity_attributes = {  # Cached known tracked entity attribute names and IDs
            # Prepopulate with attributes that are not tracked entity attributes. This allows us to treat all
            # attributes the same when adding tracked entity instances, and avoid trying to look up tracked entity
            # attribute IDs for attributes that are not tracked entity attributes.
            'Instance': 'instance',
            'Created': 'created',
            'Last updated': 'lastupdated',
            'Org unit': 'ou',
            'Tracked entity': 'te',
        }

    def _fetch_tracked_entity_attributes(self):
        __, json = self._request.get('trackedEntityAttributes', params={'links': 'false', 'paging': 'false'})
        for te in json['trackedEntityAttributes']:
            self._tracked_entity_attributes[te['name']] = te['id']

    def add_te_inst(self, data, te_name=None, ou_id=None):
        """
        Add a tracked entity instance

        :param data: A dictionary of data to post to the API
        :param te_name: Name of the tracked entity. Add or override its ID in data.
        :param ou_id: Add or override organisation unit ID in data.

        .. Note:: If te_name is not specified, then `data` must include the
                  *ID* of the tracked entity, not its name.

        """
        if te_name:
            data['Tracked entity'] = self.get_te_id(te_name)
        if ou_id:
            data['Org unit'] = ou_id
        # Convert data keys to tracked entity attribute IDs
        if any(key not in self._tracked_entity_attributes for key in data):
            # We are going to have to fetch at least one tracked entity attribute ID. Fetch them all to avoid
            # multiple API requests.
            self._fetch_tracked_entity_attributes()
        # Set instance data keys to attribute IDs
        inst = {}
        for key, value in data.iteritems():
            attr_id = self.get_te_attr_id(key)
            inst[attr_id] = value
        result = self._request.post('trackedEntityInstances', inst)
        return result

    def update_te_inst(self, data):
        """
        Update a tracked entity instance with the given data

        :param data: Tracked entity instance data. Must include its ID,
                     organisation unit and tracked entity type
        """
        for attr in ('id', 'orgUnit', 'trackedEntity'):
            if attr not in data:
                raise KeyError('Mandatory attribute "%s" missing from tracked entity instance data' % attr)
        # Convert data keys to tracked entity attribute IDs
        if any(key not in self._tracked_entity_attributes for key in data):
            self._fetch_tracked_entity_attributes()
        # Set instance data keys to attribute IDs
        inst = {self.get_te_attr_id(k): v for k, v in data.iteritems()}
        result = self._request.put('trackedEntityInstances/' + inst['id'], inst)
        return result

    def get_top_org_unit(self):
        """
        Return the top-most organisation unit.
        """
        if settings.DHIS2_ORG_UNIT:
            # A top organisation unit has been specified in the settings. Use that
            __, json = self._request.get('organisationUnits',
                                         params={'links': 'false', 'query': settings.DHIS2_ORG_UNIT})
            return json['organisationUnits'][0]
        # Traverse up the tree of organisation units
        __, org_units_json = self._request.get('organisationUnits', params={'links': 'false'})
        org_unit = org_units_json['organisationUnits'][0]
        # The List response doesn't include parent (even if you ask for it :-| ). Request org_unit details.
        __, org_unit = self._request.get('organisationUnits/' + org_unit['id'])
        while True:
            if not org_unit.get('parent'):
                # The organisation unit with no parent is the top-most organisation unit
                break
            __, org_unit = self._request.get('organisationUnits/' + org_unit['parent']['id'])
        return org_unit

    def get_resource_id(self, resource, name):
        """
        Returns the ID of the given resource type with the given name
        """
        __, json = self._request.get(resource, params={'links': 'false', 'query': name})
        if not json[resource]:
            return None
        if len(json[resource]) > 1:
            raise Dhis2ApiQueryError('Query returned multiple results')
        return json[resource][0]['id']

    def get_program_id(self, name):
        """
        Returns the ID of the given program
        """
        return self.get_resource_id('programs', name)

    def get_te_id(self, name):
        """
        Returns the ID of the given tracked entity type
        """
        return self.get_resource_id('trackedEntities', name)

    def get_te_attr_id(self, name):
        """
        Returns the ID of the given tracked entity attribute
        """
        if name not in self._tracked_entity_attributes:
            # Note: self.get_resource_id returns None if name not found
            self._tracked_entity_attributes[name] = self.get_resource_id('trackedEntityAttributes', name)
        return self._tracked_entity_attributes[name]

    def gen_instances_with_unset(self, te_name, attr_name):
        """
        Returns a list of tracked entity instances with the given attribute name unset
        """
        top_ou = self.get_top_org_unit()
        te_id = self.get_te_id(te_name)
        attr_id = self.get_te_attr_id(attr_name)
        page = 1
        while True:
            # Because we don't have an "UNSET" filter, we need to fetch all and yield the unset ones
            __, json = self._request.get(
                'trackedEntityInstances',
                params={
                    'paging': 'true',
                    'page': page,
                    'links': 'false',
                    'trackedEntity': te_id,
                    'ou': top_ou['id'],
                    'ouMode': 'DESCENDANTS',
                    'attribute': attr_id
                })
            instances = self.entities_to_dicts(json)
            for inst in instances:
                if not inst.get(attr_name):
                    yield inst
            if page < json['metaData']['pager']['pageCount']:
                page += 1
            else:
                break

    def gen_instances_with_equals(self, te_name, attr_name, attr_value):
        """
        Yields tracked entity instances with the given attribute set to the given value
        """
        top_ou = self.get_top_org_unit()
        te_id = self.get_te_id(te_name)
        attr_id = self.get_te_attr_id(attr_name)
        page = 1
        while True:
            __, json = self._request.get(
                'trackedEntityInstances',
                params={
                    'paging': 'true',
                    'page': page,
                    'links': 'false',
                    'trackedEntity': te_id,
                    'ou': top_ou['id'],
                    'ouMode': 'DESCENDANTS',
                    'attribute': attr_id + ':EQ:' + attr_value
                })
            instances = self.entities_to_dicts(json)
            for inst in instances:
                yield inst
            if page < json['metaData']['pager']['pageCount']:
                page += 1
            else:
                break

    def gen_org_units(self):
        """
        Yields organisation units
        """
        page = 1
        while True:
            __, json = self._request.get(
                'organisationUnits',
                params={
                    'paging': 'true',
                    'page': page,
                    'links': 'false'
                })
            for org_unit in json['organisationUnits']:
                yield org_unit
            if page < json['pager']['pageCount']:
                page += 1
            else:
                break

    def enroll_in(self, te_inst_id, program, when=None, data=None):
        """
        Enroll the given tracked entity instance in the given program

        :param te_inst_id: The ID of a tracked entity instance
        :param program: The *name* of a program
        :param when: The date ("YYYY-MM-DD") of enrollment. Defaults to today.
        :param data: Dictionary of additional data values of event.
        :return: The API response
        """
        program_id = self.get_resource_id('programs', program)
        return self.enroll_in_id(te_inst_id, program_id, when, data)

    def enroll_in_id(self, te_inst_id, program_id, when=None, data=None):
        """
        Enroll the given tracked entity instance in the given program

        :param te_inst_id: The ID of a tracked entity instance
        :param program_id: The ID of a program
        :param when: The date ("YYYY-MM-DD") of enrollment. Defaults to today.
        :param data: Dictionary of additional data values of event.
        :return: The API response
        """
        # cf. https://www.dhis2.org/doc/snapshot/en/user/html/ch31s34.html
        if when is None:
            when = date.today().strftime('%Y-%m-%d')
        request_data = {
            "trackedEntityInstance": te_inst_id,
            "program": program_id,
            "dateOfEnrollment": when,
            "dateOfIncident": when
        }
        if data is not None:
            if any(key not in self._tracked_entity_attributes for key in data):
                self._fetch_tracked_entity_attributes()
            request_data['dataValues'] = {self._tracked_entity_attributes[k]: v for k, v in data.iteritems()}
        __, json = self._request.post('enrollments', request_data)
        return json

    def form_to_event(self, program_id, xform, data_element_names):
        """
        Builds a dict representing a DHIS2 event

        :param program_id: The program can't be determined from form data.
        :param xform: An XFormInstance
        :param data_element_names: A dictionary mapping CCHQ form field names
                                   to DHIS2 tracked entity attribute names

        An example of an event: ::

            {
              "program": "eBAyeGv0exc",
              "orgUnit": "DiszpKrYNg8",
              "eventDate": "2013-05-17",
              "status": "COMPLETED",
              "storedBy": "admin",
              "coordinate": {
                "latitude": "59.8",
                "longitude": "10.9"
              },
              "dataValues": [
                { "dataElement": "qrur9Dvnyt5", "value": "22" },
                { "dataElement": "oZg33kd9taw", "value": "Male" },
                { "dataElement": "msodh3rEMJa", "value": "2013-05-18" }
              ]
            }

        See the DHIS2 `Events documentation`_ for more information.


        .. _Events documentation: https://www.dhis2.org/doc/snapshot/en/user/html/ch28s09.html

        """
        # For more information on the data to be sent from CCHQ to DHIS2, see
        # README.rst. Required data is given in 4.3 of the Specification
        if not any(a not in self._tracked_entity_attributes for a in data_element_names.values()):
            self._fetch_tracked_entity_attributes()
        event = {
            'program': program_id,
            'orgUnit': xform.form['dhis2_org_unit_id'],
            'eventDate': xform.received_on,
            'status': 'COMPLETED',
            'storedBy': self._username,
            'dataValues': [
                {
                    'dataElement': self._tracked_entity_attributes[te_attr_name],
                    'value': xform.form[field_name],
                } for field_name, te_attr_name in data_element_names.iteritems()
            ]
        }
        if xform.metadata.location:
            event['coordinate'] = {
                'latitude': xform.metadata.location.latitude,
                'longitude': xform.metadata.location.longitude,
            }
        return event

    def send_events(self, events):
        """
        Send events to the DHIS2 API.

        :param events: A dictionary of an event or an eventList.

        See DHIS2 `Events documentation`_ for details.


        .. _Events documentation: https://www.dhis2.org/doc/snapshot/en/user/html/ch28s09.html
        """
        __, json = self._request.post('events', events)
        return json

    @staticmethod
    def entities_to_dicts(json):
        """
        Parse the list of lists returned by a DHIS2 API entity request,
        and return it as a list of dictionaries.

        The DHIS2 API returns entity instances with a list of headers, and
        then a list of lists, as if it was dumping a spreadsheet. e.g. ::

            {
                'headers': [
                    {
                        'name': 'instance',
                        'column': 'Instance',
                        'type': 'java.lang.String',
                        'hidden': False,
                        'meta': False
                    },
                    {
                        'name': 'ou',
                        'column': 'Org unit',
                        'type': 'java.lang.String',
                        'hidden': False,
                        'meta': False
                    },
                    {
                        'name': 'dv3nChNSIxy',
                        'column': 'First name',
                        'type': 'java.lang.String',
                        'hidden': False,
                        'meta': False
                    },
                    {
                        'name': 'hwlRTFIFSUq',
                        'column': 'Last name',
                        'type': 'java.lang.String',
                        'hidden': False,
                        'meta': False
                    }
                ],
                'rows': [
                    [
                        'GpetderUTA7',
                        'Qw7c6Ckb0XC',
                        'Tesmi',
                        'Petros'
                    ],
                    [
                        'LTxvKtKq48t',
                        'Qw7c6Ckb0XC',
                        'Luwam',
                        'Rezene'
                    ],
                ]
            }

        Header "name" values like "dv3nChNSIxy" and "hwlRTFIFSUq" are not
        friendly, and so the returned dictionary uses the "column" value
        as key. The return value for this example would be ::

            [
                {
                    'Instance': 'GpetderUTA7',
                    'Org unit': 'Qw7c6Ckb0XC',
                    'First name: 'Tesmi',
                    'Last name': 'Petros'
                },
                {
                    'Instance': 'LTxvKtKq48t',
                    'Org unit': 'Qw7c6Ckb0XC',
                    'First name: 'Luwam',
                    'Last name': 'Rezene'
                }
            ]

        The row value of "Tracked entity" will look like "cyl5vuJ5ETQ".
        This isn't very friendly either. But the entity name is given in
        "metaData", which looks like this: ::

            "metaData": {
                "pager": {
                    "page": 1,
                    "total": 50,
                    "pageSize": 50,
                    "pageCount": 1
                },
                "names": {
                    "cyl5vuJ5ETQ": "Person"
                }
            }

        So we look up tracked entity names, and include them in the dictionary.

        """
        entities = []
        for row in json['rows']:
            entity = {}
            for i, item in enumerate(row):
                if json['headers'][i]['column'] == 'Tracked entity':
                    # Look up the name of the tracked entity
                    item = json['metaData']['names'][item]
                entity[json['headers'][i]['column']] = item
            entities.append(entity)
        return entities


def to_field_list(value):
    """
    Return a field value as a FieldList
    """
    return FieldList(field_list=[FixtureItemField(field_value=value, properties={})])


def to_field_value(field_list):
    """
    Return the first field value in a FieldList
    """
    return field_list.field_list[0].field_value


class FixtureManager(object):
    """
    Reuses the Django manager pattern for fixtures
    """

    def __init__(self, model_class, domain, tag):
        self.model_class = model_class
        self.domain = domain
        self.tag = tag

    def get(self, fixture_id):
        item = FixtureDataItem.get(fixture_id)
        fields = {k: to_field_value(v) for k, v in item.fields.iteritems()}
        return self.model_class(_fixture_id=item.get_id, **fields)

    def all(self):
        for item in FixtureDataItem.get_item_list(self.domain, self.tag):
            fields = {k: to_field_value(v) for k, v in item.fields.iteritems()}
            yield self.model_class(_fixture_id=item.get_id, **fields)


class Dhis2OrgUnit(object):
    """
    Simplify the management of DHIS2 Organisation Units, which are
    stored in a lookup table.
    """

    # The manager is set outside of the class definition so that we can pass
    # the class to the manager
    objects = None

    def __init__(self, id, name, _fixture_id=None):
        # It's not nice to shadow the "id" built-in, but naming the param "id"
        # allows us to pass values in from CouchDB as kwargs with less fuss.
        self.id = id
        self.name = name
        self._fixture_id = _fixture_id

    def get_id(self):
        # Pity we've got an attribute called "id" that isn't our REAL ID. This
        # returns the fixture ID.
        return self._fixture_id

    def save(self):
        data_type = FixtureDataType.by_domain_tag(self.objects.domain, self.objects.tag).one()
        if data_type is None:
            raise Dhis2ConfigurationError(
                'Unable to find lookup table in domain "%s" with ID "%s".' %
                (self.objects.domain, self.objects.tag))
        data_item = FixtureDataItem(
            data_type_id=data_type.get_id,
            domain=self.objects.domain,
            fields={
                'id': to_field_list(self.id),
                'name': to_field_list(self.name)
            })
        data_item.save()
        self._fixture_id = data_item.get_id
        return self._fixture_id

    def delete(self):
        if self._fixture_id is None:
            return
        item = FixtureDataItem.get(self._fixture_id)
        item.delete()

Dhis2OrgUnit.objects = FixtureManager(Dhis2OrgUnit, DOMAIN, LOOKUP_TABLE)