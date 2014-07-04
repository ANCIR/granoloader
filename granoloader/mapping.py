from datetime import datetime

from dateutil import parser
from granoclient.loader import Loader

BOOL_TRUISH = ['t', 'true', 'yes', 'y', '1']


def is_empty(value):
    if value is None or not len(value.strip()):
        return True
    return False


class RowException(Exception):
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
            try:
                if 'format' in spec:
                    return datetime.strptime(value, spec.get('format'))
                else:
                    return parser.parse(value)
            except:
                return None
        return value

    def get_value(self, spec, row):
        column = spec.get('column')
        if column is None:
            return
        value = row.get(column)
        if is_empty(value):
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

        for column in self.model.get('columns'):
            col_source_url = self.get_source(column, row)
            col_source_url = col_source_url or source_url

            value = self.get_value(column, row)
            if value is None and column.get('required', False):
                raise RowException('%s is not valid: %s' % (
                    column.get('column'), row.get(column.get('column'))))
            if value is None and column.get('skip_empty', True):
                continue
            obj.set(column.get('property'), value,
                    source_url=source_url)


class EntityMapper(ObjectMapper):

    def load(self, loader, row):
        source_url = self.get_source(self.model, row)
        entity = loader.make_entity(self.model.get('schemata'),
                                    source_url=source_url)
        self.load_properties(entity, row)
        entity.save()
        return entity


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
        for name, model in self.model.get('entities').items():
            yield EntityMapper(name, model)

    @property
    def relations(self):
        for name, model in self.model.get('relations').items():
            yield RelationMapper(name, model)

    def load(self, data):
        """ Load a single row of data and convert it into entities and
        relations. """
        objs = {}
        for mapper in self.entities:
            objs[mapper.name] = mapper.load(self.loader, data)

        for mapper in self.relations:
            objs[mapper.name] = mapper.load(self.loader, data, objs)
