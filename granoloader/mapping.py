from datetime import datetime
from StringIO import StringIO

import requests
from dateutil import parser
from granoclient.loader import Loader

BOOL_TRUISH = ['t', 'true', 'yes', 'y', '1']


def is_empty(value):
    if value is None or not len(value.strip()):
        return True
    return False


class RowException(Exception):
    pass


class MappingException(Exception):
    pass


class ObjectMapper(object):

    def __init__(self, name, model):
        self.name = name
        self.model = model

    def convert_type(self, value, spec):
        """ Some well-educated format guessing. """
        data_type = spec.get('type', 'string').lower().strip()
        if data_type in ['bool', 'boolean']:
            return value.lower() in BOOL_TRUISH
        elif data_type in ['int', 'integer']:
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        elif data_type in ['float', 'decimal', 'real']:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        elif data_type in ['date', 'datetime', 'timestamp']:
            if 'format' in spec:
                format_list = self._get_date_format_list(spec.get('format'))
                if format_list is None:
                    raise MappingException(
                        '%s format mapping is not valid: %r' %
                        (spec.get('column'), spec.get('format'))
                    )
                for format, precision in format_list:
                    try:
                        return {'value': datetime.strptime(value, format),
                                'value_precision': precision}
                    except (ValueError, TypeError):
                        pass
                return None
            else:
                try:
                    return parser.parse(value)
                except (ValueError, TypeError):
                    return None
        elif data_type == 'file':
            try:
                return self._get_file(value)
            except:
                raise
        return value

    def _get_date_format_list(self, format_value, precision=None):
        if isinstance(format_value, basestring):
            return [(format_value, precision)]
        elif isinstance(format_value, list):
            return [(fv, precision) for fv in format_value]
        elif isinstance(format_value, dict):
            format_list = []
            # try the most precise format first
            for key in ('time', 'day', 'month', 'year'):
                if key not in format_value:
                    continue
                format_list.extend(self._get_date_format_list(
                    format_value[key],
                    precision=key
                ))
            return format_list
        return None

    @property
    def columns(self):
        for column in self.model.get('columns'):
            if 'default' in column:
                column['required'] = False
            if column.get('skip_empty'):
                column['required'] = False
            yield self._patch_column(column)

    def _patch_column(self, column):
        return column

    def _get_file(self, url):
        response = requests.get(url)
        file_like_obj = StringIO(response.content)
        file_like_obj.name = url
        return file_like_obj

    def get_value(self, spec, row):
        """ Returns the value or a dict with a 'value' entry plus extra fields. """
        column = spec.get('column')
        default = spec.get('default')
        if column is None:
            if default is not None:
                return self.convert_type(default, spec)
            return
        value = row.get(column)
        if is_empty(value):
            if default is not None:
                return self.convert_type(default, spec)
            return None
        return self.convert_type(value, spec)

    def get_source(self, spec, row):
        """ Sources can be specified as plain strings or as a reference to a column. """
        value = self.get_value({'column': spec.get('source_url_column')}, row)
        if value is not None:
            return value
        return spec.get('source_url')

    def load_properties(self, obj, row):
        source_url = self.get_source(self.model, row)

        for column in self.columns:
            col_source_url = self.get_source(column, row)
            col_source_url = col_source_url or source_url

            value = self.get_value(column, row)
            extra_fields = {}
            if isinstance(value, dict):
                extra_fields = value
                value = extra_fields.get('value')
                del extra_fields['value']

            if value is None and column.get('required', True):
                raise RowException('%s is not valid: %s' % (
                    column.get('column'), row.get(column.get('column'))))
            if value is None and column.get('skip_empty', False):
                continue
            obj.set(column.get('property'), value,
                    source_url=source_url, **extra_fields)

            if column.get('unique', False):
                obj.unique(column.get('property'),
                           only_active=column.get('unique_active', True))


class EntityMapper(ObjectMapper):

    def load(self, loader, row):
        source_url = self.get_source(self.model, row)
        entity = loader.make_entity(self.model.get('schema'),
                                    source_url=source_url)
        self.load_properties(entity, row)
        entity.save()
        return entity

    def _patch_column(self, column):
        if column.get('property') == 'name':
            column['unique'] = True
            column['unique_active'] = False
        return column


class RelationMapper(ObjectMapper):

    def load(self, loader, row, objs):
        source_url = self.get_source(self.model, row)
        source = objs.get(self.model.get('source'))
        target = objs.get(self.model.get('target'))
        if None in [source, target]:
            return
        relation = loader.make_relation(self.model.get('schema'),
                                        source, target,
                                        source_url=source_url)
        self.load_properties(relation, row)
        relation.save()
        return relation


class MappingLoader(object):

    def __init__(self, grano, model):
        self.grano = grano
        self.loader = Loader(grano, source_url=model.get('source_url'))
        self.model = model

    @property
    def entities(self):
        for name, model in self.model.get('entities', {}).items():
            yield EntityMapper(name, model)

    @property
    def relations(self):
        for name, model in self.model.get('relations', {}).items():
            yield RelationMapper(name, model)

    def load(self, data):
        """ Load a single row of data and convert it into entities and
        relations. """
        objs = {}
        for mapper in self.entities:
            objs[mapper.name] = mapper.load(self.loader, data)

        for mapper in self.relations:
            objs[mapper.name] = mapper.load(self.loader, data, objs)
