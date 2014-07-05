import os
import click
import logging

import yaml
from unicodecsv import DictReader
from granoclient import Grano, GranoException
from thready import threaded

from granoloader.mapping import MappingLoader, RowException

logging.basicConfig(level=logging.WARN)

gc_log = logging.getLogger("granoclient")
gc_log.setLevel(logging.ERROR)

log = logging.getLogger()


def make_client(host, project_name, api_key):
    """ Instantiate the grano client based on environment variables or
    command line settings. """
    if host is None:
        raise click.BadParameter('No grano server host is set', param=host)
    if project_name is None:
        raise click.BadParameter('No grano project slug is set',
                                 param=project_name)
    if api_key is None:
        raise click.BadParameter('No grano API key is set', param=api_key)

    client = Grano(api_host=host,
                   api_key=api_key)
    return client.get(project_name)


def init():
    app(obj={})


@click.group()
@click.option('--host', '-h', envvar='GRANO_HOST',
              help='Host name of the grano instance to be loaded')
@click.option('--project', '-p', envvar='GRANO_PROJECT',
              help='Project slug to be loaded')
@click.option('--api-key', '-k', envvar='GRANO_APIKEY',
              help='API key with write access to the project')
@click.pass_context
def app(ctx, host, project, api_key):
    ctx.obj['grano'] = make_client(host, project, api_key)


@app.command()
@click.option('--force', '-f', default=False, is_flag=True,
              help='Continue loading upon errors')
@click.option('--threads', '-t', default=1, type=int,
              help='Parallel threads to run')
@click.argument('mapping', type=click.File('rb'))
@click.argument('data', type=click.File('rb'))
@click.pass_context
def csv(ctx, force, threads, mapping, data):
    """ Load CSV data into a grano instance using a mapping specification. """

    # Find out how many lines there are (for the progress bar).
    lines = 0
    for line in DictReader(data):
        lines += 1
    data.seek(0)

    # set up objects
    mapping = yaml.load(mapping)
    mapping_loader = MappingLoader(ctx.obj['grano'], mapping)

    def process_row(row):
        try:
            mapping_loader.load(row)
        except GranoException, ge:
            msg = '\nServer error: %s' % ge.message
            click.secho(msg, fg='red', bold=True)
            if not force:
                os._exit(1)
        except RowException, re:
            msg = '\nRow %s: %s' % (row['__row_id__'], re.message)
            click.secho(msg, fg='red', bold=True)
            if not force:
                os._exit(1)

    def generate():
        with click.progressbar(DictReader(data),
                               label=data.name,
                               length=lines) as bar:
            for i, row in enumerate(bar):
                row['__row_id__'] = i
                yield row

    threaded(generate(), process_row, num_threads=threads,
             max_queue=1)


@app.command()
@click.argument('schema', type=click.File('rb'))
@click.pass_context
def schema(ctx, schema):
    """ Load schema definitions from a YAML file. """
    data = yaml.load(schema)
    if not isinstance(data, (list, tuple)):
        data = [data]
    with click.progressbar(data, label=schema.name) as bar:
        for schema in bar:
            ctx.obj['grano'].schemata.upsert(schema)
