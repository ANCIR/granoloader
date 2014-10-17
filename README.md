# granoloader

A simple command-line tool to load grano data from CSV files. Data is
loaded via the REST API, and the library performs updates as well as
inserting new data.

## Usage

The command can be used to load CSV files like this:

    granoloader csv mapping_file.yaml data_file.csv

Similarly, schema definitions can be loaded from a YAML file:

    granoloader schema schema-definitions.yaml
	
To load data to a grano instance, you will also need to set the grano
host name, api key and project name. These can be provided through the
command line, but it might be more convenient to set the following 
environment variables:

* ``GRANO_HOST`` for the host name
* ``GRANO_PROJECT`` as a project slug
* ``GRANO_APIKEY`` as the API key of an account with write access to
  the given project.

## Mapping files

Since the association between input file columns and the properties of
the entities and relations cannot be inferred easily, an explicit
mapping is required to be given in the form of a YAML file.

### File format

The YAML file must have sections to define which set of entities and 
relations should be generated from each row of the input data. This
can be used to import either a single entity per row, two entities and
a relation between them, or any other, more complex, set of linkages.

Imagine, for example, importing company directorships:

```yaml
 entities:
   director:
     schema: 'Person'
   company:
     schema: 'Company'
 relations:
 	 directorship:
 	   schema: 'directorship'
 	   source: 'director'
 	   target: 'company'
```

After these objects have been defined, the individual meanings of the
columns can be defined by referencing the prepared objects:

```yaml
entities:
  director:
    schema: 'Person'
    columns:
	    - column: 'director_name'
	      property: 'name'
	      required: true
      - column: 'director_gender'
        property: 'gender'
        skip_empty: true
  company:
    schema: 'Company'
    columns: 	
	    - column: 'company_name'
	      property: 'name'
	      required: true
relations:
  directorship:
    schema: 'directorship'
	  source: 'director'
	  target: 'company'
	  columns: []
```

The ``skip_empty`` field will make sure that when the cell for
``director_gender`` is empty, no property will be set on the imported 
entity (rather than creating a property with a null value).

### Source annotation

Finally, you can add information on the source of each row or even cell
of the data. On the level of the ``mapping``, you can set a key for 
``source_url`` that will be applied to all entities and relations. In 
each entity or relation, you can either set ``source_url`` to give a 
string URL, or ``source_url_column`` to reference the value of a specific
column and take its value as the source. The same can be done on a
per-column basis.

### Type conversion

If you want to import non-string property values, you can set ``type``
on the appropriate column specification to convert the data. Valid types include ``int``, ``float``, ``boolean``, ``datetime`` and ``file``.

#### Datetime format

For ``datetime``, a further setting, ``format`` can be given as one or more Python date format strings. If it is not specified, the date format will be guessed. The most basic usage is a single format string:

```YAML
format: '%d/%m/%Y'
```

To allow dates in multiple formats to be parsed correctly, a list of formats can be supplied:

```YAML
format: ['%d/%m/%Y', '%d-%m-%Y', '%m/%Y', '%m-%Y']
```

Datetime values can include a precision specifier. Valid specifiers are 'time', 'day', 'month' and 'year' (from most to least precise). To load both date value and precision, provide a format mapping for one or more of the precision specifiers:

```YAML
format:
  day: ['%d-%m-%Y', '%d/%m/%Y']
  month: ['%m-%Y', '%m/%Y']
  year: '%Y'
```

#### File URL

The ``file`` type expects a url string. ``granoloader`` will retrieve the file at the url.
