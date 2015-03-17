User Configurable Reporting
===========================

An overview of the design, API and data structures used here.

# Data Flow

Reporting is handled in multiple stages. Here is the basic workflow.

Raw data (form or case) → [Data source config] → Row in database table → [Report config] → Report in HQ

Both the data source config and report config are JSON documents that live in the database. The data source config determines how raw data (forms and cases) gets mapped to rows in an intermediary table, while the report config(s) determine how that report table gets turned into an interactive report in the UI.

# Data Sources

Each data source configuration maps a filtered set of the raw data to indicators. A data source configuration consists of two primary sections:

1. A filter that determines whether the data is relevant for the data source
2. A list of indicators in that data source

In addition to these properties there are a number of relatively self-explanatory fields on a data source such as the `table_id` and `display_name`, and a few more nuanced ones. The full list of available fields is summarized in the following table:

Field                | Description
-------------------- | -----------
filter               | Determines whether the data is relevant for the data source
indicators           | List of indicators to save
table_id             | A unique ID for the table
display_name         | A display name for the table that shows up in UIs
base_item_expression | Used for making tables off of repeat or list data
named_filters        | A list of named filters that can be referenced in other filters and indicators


## Data Source Filtering

When setting up a data source configuration, filtering defines what data applies to a given set of indicators. Some example uses of filtering on a data source include:

- Restricting the data by document type (e.g. cases or forms). This is a built-in filter.
- Limiting the data to a particular case or form type
- Excluding demo user data
- Excluding closed cases
- Only showing data that meets a domain-specific condition (e.g. pregnancy cases opened for women over 30 years of age)

### Filter type overview

There are currently four supported filter types. However, these can be used together to produce arbitrarily complicated expressions.


Filter Type        | Description
------------------ | -----------
boolean_expression | A expression / logic statement (more below)
and                | An "and" of other filters - true if all are true
or                 | An "or" of other filters - true if any are true
not                | A "not" or inverse expression on a filter

To understand the `boolean_expression` type, we must first explain expressions.

### Expressions

An *expression* is a way of representing a set of operations that should return a single value. Expressions can basically be thought of as functions that take in a document and return a value:

*Expression*: `function(document) → value`

In normal math/python notation, the following are all valid expressions on a `doc` (which is presumed to be a `dict` object:

- `"hello"`
- `7`
- `doc["name"]`
- `doc["child"]["age"]`
- `doc["age"] < 21`
- `"legal" if doc["age"] > 21 else "underage"`

In user configurable reports the following expression types are currently supported (note that this can and likely will be extended in the future):

Expression Type | Description  | Example
--------------- | ------------ | ------
constant        | A constant   | `"hello"`, `4`, `2014-12-20`
property_name   | A reference to the property in a document |  `doc["name"]`
property_path   | A nested reference to a property in a document | `doc["child"]["age"]`
conditional     | An if/else expression | `"legal" if doc["age"] > 21 else "underage"`
related_doc     | A way to reference something in another document | `form.case.owner_id`
root_doc        | A way to reference the root document explicitly (only needed when making a data source from repeat/child data) | `repeat.parent.name`

### JSON snippets for expressions

Here are JSON snippets for the four expression types. Hopefully they are self-explanatory.

##### Constant Expression

This expression returns the constant "hello":
```
{
    "type": "constant",
    "constant": "hello"
}
```
##### Property Name Expression

This expression returns `doc["age"]`:
```
{
    "type": "property_name",
    "property_name": "age"
}
```
An optional `"datatype"` attribute may be specified, which will attempt to cast the property to the given data type. The options are "date", "datetime", "string", "integer", and "decimal". If no datatype is specified, "string" will be used.
##### Property Path Expression

This expression returns `doc["child"]["age"]`:
```
{
    "type": "property_name",
    "property_path": ["child", "age"]
}
```
An optional `"datatype"` attribute may be specified, which will attempt to cast the property to the given data type. The options are "date", "datetime", "string", "integer", and "decimal". If no datatype is specified, "string" will be used.
##### Conditional Expression

This expression returns `"legal" if doc["age"] > 21 else "underage"`:
```
{
    "type": "conditional",
    "test": {
        "operator": "gt",
        "expression": {
            "type": "property_name",
            "property_name": "age"
            "datatype": "integer"
        },
        "type": "boolean_expression",
        "property_value": 21
    },
    "expression_if_true": {
        "type": "constant",
        "property_name": "legal"
    },
    "expression_if_false": {
        "type": "constant",
        "property_name": "underage"
    }
}
```
Note that this expression contains other expressions inside it! This is why expressions are powerful. (It also contains a filter, but we haven't covered those yet - if you find the `"test"` section confusing, keep reading...)

Note also that it's important to make sure that you are comparing values of the same type. In this example, the expression that retrieves the age property from the document also casts the value to an integer. If this datatype is not specified, the expression will compare a string to the `21` value, which will not produce the expected results! 

#### Related document expressions

This can be used to lookup a property in another document. Here's an example that lets you look up `form.case.owner_id` from a form.

```
{
    "type": "related_doc",
    "related_doc_type": "CommCareCase",
    "doc_id_expression": {
        "type": "property_path",
        "property_path": ["form", "case", "@case_id"]
    },
    "value_expression": {
        "type": "property_name",
        "property_name": "owner_id"
    }
}
```

### Boolean Expression Filters

A `boolean_expression` filter combines an *expression*, an *operator*, and a *property value* (a constant), to produce a statement that is either `True` or `False`. *Note: in the future the constant value may be replaced with a second expression to be more general, however currently only constant property values are supported.*

Here is a sample JSON format for simple `boolean_expression` filter:
```
{
    "type": "boolean_expression",
    "expression": {
        "type": "property_name",
        "property_name": "age",
        "datatype": "integer"
    },
    "operator": "gt",
    "property_value": 21
}
```
This is equivalent to the python statement: `doc["age"] > 21`

#### Operators

The following operators are currently supported:

Operator   | Description  | Value type | Example
---------- | -----------  | ---------- | -------
`eq`       | is equal     | constant   | `doc["age"] == 21`
`not_eq`   | is not equal | constant   | `doc["age"] != 21`
`in`       | single value is in a list | list | `doc["color"] in ["red", "blue"]`
`in_multi` | multiselect value is in a list | list | `selected(doc["color"], ["red", "blue"])`
`lt`       | is less than | number | `doc["age"] < 21`
`lte`      | is less than or equal | number | `doc["age"] <= 21`
`gt`       | is greater than | number | `doc["age"] > 21`
`gte`      | is greater than or equal | number | `doc["age"] >= 21`

### Compound filters

Compound filters build on top of `boolean_expression` filters to create boolean logic. These can be combined to support arbitrarily complicated boolean logic on data. There are three types of filters, *and*, *or*, and *not* filters. The JSON representation of these is below. Hopefully these are self explanatory.

#### "And" Filters

The following filter represents the statement: `doc["age"] < 21 and doc["nationality"] == "american"`:
```
{
    "type": "and",
    "filters": [
		{
            "type": "boolean_expression",
            "expression": {
                "type": "property_name",
                "property_name": "age",
                "datatype": "integer"
            },
            "operator": "lt",
            "property_value": 21
        },
        {
            "type": "boolean_expression",
            "expression": {
                "type": "property_name",
                "property_name": "nationality",
            },
            "operator": "eq",
            "property_value": "american"
        }
    ]
}
```
#### "Or" Filters

The following filter represents the statement: `doc["age"] > 21 or doc["nationality"] == "european"`:
```
{
    "type": "or",
    "filters": [
		{
            "type": "boolean_expression",
            "expression": {
                "type": "property_name",
                "property_name": "age",
                "datatype": "integer",
            },
            "operator": "gt",
            "property_value": 21
        },
		{
            "type": "boolean_expression",
            "expression": {
                "type": "property_name",
                "property_name": "nationality",
            },
            "operator": "eq",
            "property_value": "european"
        }
    ]
}
```
#### "Not" Filters

The following filter represents the statement: `!(doc["nationality"] == "european")`:
```
{
    "type": "not",
    "filter": [
        {
            "type": "boolean_expression",
            "expression": {
                "type": "property_name",
                "property_name": "nationality",
            },
            "operator": "eq",
            "property_value": "european"
        }
    ]
}
```
*Note that this could be represented more simply using a single filter with the `not_eq` operator, but "not" filters can represent more complex logic than operators generally, since the filter itself can be another compound filter.*

### Practical Examples

Below are some practical examples showing various filter types.

#### Matching form submissions from a particular form type

```
{
    "type": "boolean_expression",
    "expression": {
        "type": "property_name",
        "property_name": "xmlns",
    },
    "operator": "eq",
    "property_value": "http://openrosa.org/formdesigner/my-registration-form"
}
```
#### Matching cases of a specific type

```
{
    "type": "boolean_expression",
    "expression": {
        "type": "property_name",
        "property_name": "type",
    },
    "operator": "eq",
    "property_value": "child"
}
```

## Indicators

Now that we know how to filter the data in our data source, we are still left with a very important problem: *how do we know what data to save*? This is where indicators come in. Indicators are the data outputs - what gets computed and put in a column in the database.

A typical data source will include many indicators (data that will later be included in the report). This section will focus on defining a single indicator. Single indicators can then be combined in a list to fully define a data source.

The overall set of possible indicators is theoretically any function that can take in a single document (form or case) and output a value. However the set of indicators that are configurable is more limited than that.

### Indicator Properties

All indicator definitions have the following properties:

Property        | Description
--------------- | -----------
type            | A specified type for the indicator. It must be one of the types listed below.
column_id       | The database column where the indicator will be saved.
display_name    | A display name for the indicator (not widely used, currently).

Additionally, specific indicator types have other type-specific properties. These are covered below.

### Indicator types

The following primary indicator types are supported:

Indicator Type | Description
-------------- | -----------
boolean        | Save `1` if a filter is true, otherwise `0`.
expression     | Save the output of an expression.
choice_list    | Save multiple columns, one for each of a predefined set of choices

*Note/todo: there are also other supported formats, but they are just shortcuts around the functionality of these two so they are left out of the current docs.*

#### Boolean indicators

Now we see again the power of our filter framework defined above! Boolean indicators take any arbitrarily complicated filter expression and save a `1` to the database if the expression is true, otherwise a `0`.  Here is an example boolean indicator which will save `1` if a form has a question with ID `is_pregnant` with a value of `"yes"`:

```
{
    "type": "boolean",
    "column_id": "col",
    "filter": {
	    "type": "boolean_expression",
	    "expression": {
	        "type": "property_path",
	        "property_path": ["form", "is_pregnant"],
	    },
	    "operator": "eq",
	    "property_value": "yes"
	}
}
```

#### Expression indicators

Similar to the boolean indicators - expression indicators leverage the expression structure defined above to create arbitrarily complex indicators. Expressions can store arbitrary values from documents (as opposed to boolean indicators which just store `0`'s and `1`'s). Because of this they require a few additional properties in the definition:

Property        | Description
--------------- | -----------
datatype        | The datatype of the indicator. Current valid choices are: "date", "datetime", "string", "decimal", and "integer".
is_nullable     | Whether the database column should allow null values.
is_primary_key  | Whether the database column should be (part of?) the primary key. (TODO: this needs to be confirmed)
expression      | Any expression.

Here is a sample expression indicator that just saves the "age" property to an integer column in the database:

```
{
    "type": "expression",
    "expression": {
        "type": "property_name",
        "property_name": "age"
    },
    "column_id": "age",
    "datatype": "integer",
    "display_name": "age of patient"
}
```

### Practical notes for creating indicators

These are some practical notes for how to choose what indicators to create.

#### Fractions

All indicators output single values. Though fractional indicators are common, these should be modeled as two separate indicators (for numerator and denominator) and the relationship should be handled in the report UI config layer.

## Saving Repeat Data

You can save data from a repeatable or child element in a form by specifying a root level `base_item_expression` that describes how to get the repeat data from the main document. You can also use the `root_doc` expression type to reference parent properties. This is not described in detail, but the following sample (which creates a table off of a repeat element called "time_logs" can be used as a guide):

```
{
    "domain": "user-reports",
    "doc_type": "DataSourceConfiguration",
    "referenced_doc_type": "XFormInstance",
    "table_id": "sample-repeat",
    "display_name": "Time Logged",
    "base_item_expression": {
        "type": "property_path",
        "property_path": ["form", "time_logs"]
    },
    "configured_filter": {
    },
    "configured_indicators": [
        {
            "type": "expression",
            "expression": {
                "type": "property_name",
                "property_name": "start_time"
            },
            "column_id": "start_time",
            "datatype": "datetime",
            "display_name": "start time"
        },
        {
            "type": "expression",
            "expression": {
                "type": "property_name",
                "property_name": "end_time"
            },
            "column_id": "end_time",
            "datatype": "datetime",
            "display_name": "end time"
        },
        {
            "type": "expression",
            "expression": {
                "type": "property_name",
                "property_name": "person"
            },
            "column_id": "person",
            "datatype": "string",
            "display_name": "person"
        },
        {
            "type": "expression",
            "expression": {
                "type": "root_doc",
                "expression": {
                    "type": "property_name",
                    "property_name": "name"
                }
            },
            "column_id": "name",
            "datatype": "string",
            "display_name": "name of ticket"
        }
    ]
}
```

# Report Configurations

A report configuration takes data from a data source and renders it in the UI. A report configuration consists of a few different sections:

1. A list of filter fields. These map to filters that show up in the UI, and should translate to queries that can be made to limit the returned data.
2. A list of aggregation fields. These defines how indicator data will be aggregated into rows in the report. The complete list of aggregations fields forms the *primary key* of each row in the report.
3. A list of columns. Columns define the report columns that show up from the data source, as well as any aggregation information needed.

## Samples

Here are some sample configurations that can be used as a reference until we have better documentation.

- [Dimagi chart report](https://github.com/dimagi/commcare-hq/blob/master/commcarehq/apps/userreports/examples/dimagi/dimagi-chart-report.json)
- [GSID form report](https://github.com/dimagi/commcare-hq/blob/master/commcarehq/apps/userreports/examples/gsid/gsid-form-report.json)


## Report filters

The documentation for report filters is still in progress. Apologies for brevity below.

**A note about report filters versus data source filters**

Report filters are _completely_ different from data source filters. Data source filters limit the global set of data that ends up in the table, whereas report filters allow you to select values to limit the data returned by a query.

### Numeric Filters
Numeric filters allow users to filter the rows in the report by comparing a column to some constant that the user specifies when viewing the report.
Numeric filters are only intended to be used with numeric (integer or decimal type) columns. Supported operators are =, &ne;, &lt;, &le;, &gt;, and &ge;.

ex:
```
{
  "type": "numeric",
  "slug": "number_of_children_slug",
  "field": "number_of_children",
  "display": "Number of Children"
}
```

### Date filters

Date filters allow you filter on a date. They will show a datepicker in the UI.

```
{
  "type": "date",
  "slug": "modified_on",
  "field": "modified_on",
  "display": "Modified on",
  "required": false
}
```

### Dynamic choice lists

Dynamic choice lists provide a select widget that shows all possible values for a column.

```
{
  "type": "dynamic_choice_list",
  "slug": "village",
  "field": "village",
  "display": "Village",
  "datatype": "string"
}
```

### Choice lists

Choice lists allow manual configuration of a fixed, specified number of choices and let you change what they look like in the UI.
```
{
  "type": "choice_list",
  "slug": "role",
  "field": "role",
  "choices": [
    {"value": "doctor", display:"Doctor"},
    {"value": "nurse"}
  ]
}
```

## Report Columns

TODO: Report column docs will go here.

Here's an example report column that shows the owner name from an associated `owner_id`:

```
{
    "type": "field",
    "field": "owner_id",
    "display": "Owner Name"
    "format": "default",
    "transform": {
        "type": "custom",
        "custom_type": "owner_display"
    },
    "aggregation": "simple",
}
```

### Transforms

Transforms can be used to transform the value returned by a column just before it reaches the user. Currently there are four supported transform types. These are shown below:

#### Displaying username instead of user ID

```
{
    "type": "custom",
    "custom_type": "user_display"
}
```

#### Displaying username minus @domain.commcarehq.org instead of user ID

```
{
    "type": "custom",
    "custom_type": "user_without_domain_display"
}
```

#### Displaying owner name instead of owner ID

```
{
    "type": "custom",
    "custom_type": "owner_display"
}
```

#### Displaying month name instead of month index

```
{
    "type": "custom",
    "custom_type": "month_display"
}
```

# Practical Notes

Some rough notes for working with user configurable reports.

## Getting Started


The easiest way to get started is to start with sample data and reports.

First copy the dimagi domain to your developer machine.
You only really need forms, users, and cases:

```
./manage.py copy_domain https://<your_username>:<your_password>@commcarehq.cloudant.com/commcarehq dimagi --include=CommCareCase,XFormInstance,CommCareUser
```

Then load and rebuild the data table:

```
./manage.py load_spec commcarehq/apps/userreports/examples/dimagi/dimagi-case-data-source.json --rebuild
```

Then load the report:

```
./manage.py load_spec commcarehq/apps/userreports/examples/dimagi/dimagi-chart-report.json
```

Fire up a browser and you should see the new report in your domain.
You should also be able to navigate to the edit UI, or look at and edit the example JSON files.
There is a second example based off the "gsid" domain as well using forms.

The tests are also a good source of documentation for the various filter and indicator formats that are supported.

## Static data sources

As well as being able to define data sources via the UI which are stored in the database you
can also define static data sources which live as JSON documents in the source repository.

These are mainly useful for custom reports.

They conform to a slightly different style:
```
{
    "domains": ["live-domain", "test-domain"],
    "config": {
        ... put the normal data source configuration here
    }
}
```

Having defined the data source you need to add the path to the data source file to the `CUSTOM_DATA_SOURCES`
setting in `settings.py`. Now when the `CustomDataSourcePillow` is run it will pick up the data source
and rebuild it.

Changes to the data source require restarting the pillow which will rebuild the SQL table. Alternately you
can use the UI to rebuild the data source (requires Celery to be running).


## Inspecting database tables


The easiest way to inspect the database tables is to use the sql command line utility.
This can be done by runnning `./manage.py dbshell` or using `psql`.
The naming convention for tables is: `configurable_indicators_[domain name]_[table id]_[hash]`.
In postgres, you can see all tables by typing `\dt` and use sql commands to inspect the appropriate tables.