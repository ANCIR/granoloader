import click
import logging
import yaml
from unicodecsv import DictReader
from granoclient import Grano, GranoException

from granoloader.mapping import MappingLoader, RowException

logging.basicConfig(level=logging.WARN)
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


@click.command()
@click.option('--host', '-h', envvar='GRANO_HOST',
              help='Host name of the grano instance to be loaded')
@click.option('--project', '-p', envvar='GRANO_PROJECT',
              help='Project slug to be loaded')
@click.option('--api-key', '-k', envvar='GRANO_APIKEY',
              help='API key with write access to the project')
@click.option('--force', '-f', default=False, is_flag=True,
              help='Continue loading upon errors')
@click.argument('mapping', type=click.File('rb'))
@click.argument('data', type=click.File('rb'))
def load(host, project, api_key, force, mapping, data):
    """ Load CSV data into a grano instance using a mapping specification. """

    # Find out how many lines there are (for the progress bar).
    lines = 0
    for line in data.xreadlines():
        lines += 1
    data.seek(0)

    # set up objects
    grano = make_client(host, project, api_key)
    mapping = yaml.load(mapping)
    mapping_loader = MappingLoader(grano, mapping)

    with click.progressbar(DictReader(data),
                           label=data.name,
                           length=lines) as bar:
        for i, row in enumerate(bar):
            try:
                mapping_loader.load(row)
            except GranoException, ge:
                msg = '\nServer error: %s' % ge.message
                click.secho(msg, fg='red', bold=True)
                if not force:
                    return -1
            except RowException, re:
                msg = '\nRow %s: %s' % (i, re.message)
                click.secho(msg, fg='red', bold=True)
                if not force:
                    return -1
