# Overview
- Filter syntax is based on [JSONLogic](https://jsonlogic.com/) (an [AST](https://en.wikipedia.org/wiki/Abstract_syntax_tree)) and thus defined as [JSON](https://en.wikipedia.org/wiki/JSON).
-  Some but not all of the standard [JSONLogic operations](https://jsonlogic.com/operations.html) are supported.
- In addition to the subset of standard operations, some custom operators have been added for the purposes of semantic search capabilities.

[Jump to start of syntax definitions](#grammar).

# Full syntax example
- The following illustrates most of the available Advanced Search syntax.
- The query is written as [yaml](https://en.wikipedia.org/wiki/YAML) so comments can be included but this is valid JSON if the comments are removed.

```yaml
{
    # Aliases for ontologies to reference in the filter
    "prefixes": {
        "rail": "http://example.org/ontology/rail/",
        "battery": "http://example.org/ontology/batteries/",
        "custom": "http://example.org/ontology/myUnits#",
        "iotics": "http://data.iotics.com/iotics#",
        "pub": "http://data.iotics.com/public#"
    },
    "filter": {"or": [
        {"and": [
            # The twin is an engine
            {"==": [["$twin", "rdf:type"], "rail:Engine"]},
            # It has an Input with the charging capacity property (any value)
            {"has": ["$input", "rail:chargingCapacity"]},
            # It has been created before 2011-01-10
            {"<": [["$twin", "iotics:createdAt"], {"strdt": ["2011-01-10", "xsd:date"]}]},
            # Same condition as above but with implied $twin binding
            {"<": ["iotics:createdAt", {"strdt": ["2011-01-10", "xsd:date"]}]},
            # Twin has allow-all entry for metadata visibility (selective metadata sharing)
            {"==": ["pub:hostMetadataAllowList", "pub:allHosts"]}
        ]},
        {"and": [
            # Has a feed representing a battery (from one of two ontological classes)
            {"in": [["$feed", "rdf:type"], ["rail:Battery", "batteries:LeadAcid"]]},
            # Said battery is not operational
            {"!=": [["$feed", "rail:isOperational"], true]},
            # same condition as above but with explicit type (rather than implicit)
            {"!=": [["$feed", "rail:isOperational"], {"strdt": ["true", "xsd:boolean"]}]},
            {"or": [
                # The twin is within 2.5km of the station in either Bury St Edmunds or Cambridge
                {"spatial-nearby": ["$twin", [52.25361, 0.7119368, 2.5]]},
                {"spatial-nearby": ["$twin", [52.194156,0.1372278, 2.5]]}
            ]},
            # Example of specifying full IRI in property path
            {"has": ["$twin", {"iri": "http://example.org/ontology/bahn/kupplung"}]},
            # Custom unit matching (implied twin subject)
            {"==": ["rail:anotherProperty", {"strdt": ["custom-encoding", "custom:someUnit"]}]},
            # same as above with explicit RELative IRI
            {"==": ["rail:anotherProperty", {"strdt": ["custom-encoding", {"rel": "custom:someUnit"}]}]},
            # same as above but with full IRI unit
            {"==": ["rail:anotherProperty", {"strdt": [
                "custom-encoding", {"iri": "http://example.org/ontology/myUnits#custom:someUnit"}
            ]}]}
        ]},
        # Twin has no feeds
        {"!": {
            "has": ["$feed", "rdf:type"]
        }}
    ]}
}
```

# <a name="grammar"></a>Grammar

<pre>
<a href="#top-level">TOP_LEVEL</a>: {("prefixes": {<a href="#prefix">PREFIX</a>, ...},) "filter": <a href="#condition">CONDITION<a>}
<a href="#prefix">PREFIX</a>: "alias": "namespace-uri"

<a href="#condition">CONDITION</a>: <a href="#cond-comparison">COND_COMPARISON</a> | <a href="#cond-in">COND_IN</a> | <a href="#cond-has">COND_HAS</a> | <a href="#cond-spatial-nearby">COND_SPATIAL_NEARBY</a> | <a href="#cond-logic">COND_LOGIC</a> | <a href="#cond-not">COND_NOT</a>

<a href="#cond-comparison">COND_COMPARISON</a>: {COMPARE_OP: [<a href="#property-path">PROPERTY_PATH</a>,  <a href="#values">VALUE</a>]}
COMPARE_OP: "==" | "!=" | ">" | ">=" | "<" | "<="

<a href="#cond-in">COND_IN</a>: {"in": [<a href="#property-path">PROPERTY_PATH</a>,  [<a href="#values">VALUE</a>, <a href="#values">VALUE</a>, ...]}

<a href="#cond-has">COND_HAS</a>: {"has": <a href="#property-path">PROPERTY_PATH</a>}

<a href="#cond-spatial-nearby">COND_SPATIAL_NEARBY</a>: {"spatial-nearby": [<a href="#binding">BINDING</a>, [LAT, LONG, RADIUS]]}

<a href="#cond-logic">COND_LOGIC</a>: {LOGIC_OP: [<a href="#condition">CONDITION</a>, <a href="#condition">CONDITION</a>, ...]}
LOGIC_OP: "and" | "or"

<a href="#cond-not">COND_NOT</a>: {"!": <a href="#condition">CONDITION</a>}

<a href="#property-path">PROPERTY_PATH</a> = VALUE_REL_IMPLICIT | FULL_PROPERTY_PATH
FULL_PROPERTY_PATH: [<a href="#binding">BINDING</a>, <a href="#link">LINK</a>]

<a href="#binding">BINDING</a>: "$twin" | "$feed" | "$input"

<a href="#link">LINK</a>: <a href="#val-iri">VALUE_IRI</a> | <a href="#val-rel">VALUE_REL</a> | VALUE_REL_IMPLICIT

<a href="#values">VALUE</a>: <a href="#val-iri">VALUE_IRI</a> | <a href="#val-rel">VALUE_REL</a> | <a href="#values-implicit">&lt;JSON_STRING&gt;</a> | <a href="#values-implicit">&lt;JSON_TRUE&gt;</a> | <a href="#values-implicit">&lt;JSON_FALSE&gt;</a> | <a href="#values-implicit">&lt;JSON_NUMBER&gt;</a>

<a href="#val-iri">VALUE_IRI</a>: {"iri": "iri-value"}
<a href="#val-rel">VALUE_REL</a>: {"rel": VALUE_REL_IMPLICIT}
VALUE_REL_IMPLICIT: "alias:iri-suffix"

<a href="#val-lang-str">VALUE_LANG_STRING</a>: {"strlang": ["string value", "&lt;ISO 639-1 code&gt;"]}

<a href="#val-literal">VALUE_LITERAL</a>: {"strdt": ["encoded value", <a href="#link">LINK</a>]}
</pre>

# <a name="top-level"></a>Top level
<pre>
{
    "prefixes": {
        <a href="#prefix">PREFIX</a>,
        ...
    },
    "filter": <a href="#condition">CONDITION</a>
}
</pre>

- The `prefixes` section is optional.


# <a name="prefix"></a>Prefixes
Expression of property names (and IRI property values) can be made more concise by using prefixes for commonly used namespaces. This involves choosing an alias for an ontology, defining its URI in the prefix section and subsequently referring to it in the filter.

```
"alias": "namespace-uri"
```

- Each alias must be unique
- Aliases can only use alphanumeric characters
- Namespaces must be a valid IRIs
- The following prefixes are automatically defined and cannot be overridden:
    - [`xsd`](http://www.w3.org/2001/XMLSchema#) - data types such as xsd:integer
    - [`rdf`](http://www.w3.org/1999/02/22-rdf-syntax-ns#) - ontology references such as rdf:Property
    - [`rdfs`](http://www.w3.org/2000/01/rdf-schema#) - ontology references as well as e.g. text fields such as rdfs:label

## Example
```json
{
    "prefixes": {
        "rail": "http://example.org/ontology/rail/",
        "engines": "http://example.org/ontology/engines/"
    },
    "filter": {"==": ["rail:engineType", "engines:Diesel"]}
}
```

Thereafter one can use the `rail:` prefix to refer to this ontology, e.g. `"rail:wheelCount"` (instead of having to write `"http://example.org/ontology/rail/wheelCount"`).


# <a name="condition"></a>Conditions
```
{OPERATOR: ARGUMENTS}
```
- `OPERATOR` is one of:
    - [`"=="`](#cond-comparison)
    - [`"!="`](#cond-comparison)
    - [`">"`](#cond-comparison)
    - [`">="`](#cond-comparison)
    - [`"<"`](#cond-comparison)
    - [`"<="`](#cond-comparison)
    - [`"in"`](#cond-in)
    - [`"has"`](#cond-has)
    - [`"spatial-nearby"`](#cond-spatial-nearby)
    - [`"and"`](#cond-logic)
    - [`"or"`](#cond-logic)
    - [`"!"`](#cond-not)
- `ARGUMENTS` are specific to a given operator


## <a name="cond-comparison"></a>Comparison
The classic search API [only supports](https://github.com/Iotic-Labs/api/blob/55f8e8a9e8a48dffd3b5a8b526b4b3f975c4bc60/proto/iotics/api/search.proto#L64-L65) equality matching of predicates. This has now been expanded to a full set of rich comparison operators.

<pre>
{COMPARE_OP: [<a href="#property-path">PROPERTY_PATH</a>,  <a href="#values">VALUE</a>]}
</pre>

- `COMPARE_OP` is one of:

    Op      | Meaning
    ------- | ---------
    `==`    | equal
    `!=`    | not equal
    `>`     | greater
    `>=`    | greater or equal
    `<`     | smaller
    `<=`    | smaller or equal

### Value (data type) compatibility
Whether a comparison is possible, depends on the object and reference term (data) types. These fall into the following categories:

Type | Comparison restrictions
---  | ---
Numeric | Any [`xsd:` namespace](http://www.w3.org/2001/XMLSchema#) numeric types can be compared against each other (this includes implicit ones - see [here](#values-implicit))
Boolean | `xsd:boolean` can only be compared against another `xsd:boolean`
Date Time | `xsd:dateTime` can only be compared against another `xsd:dateTime`
String | `xsd:string` (implicit or explicit) can only be compared against another `xsd:string` if both have the same language or no language
IRI | IRIs (see [Values](#values)) can only be compared against other IRIs (in either [prefix](#val-rel) or [full](#val-iri) forms)
RDF literal | Any other [literals](#val-literal) support only equality ([`==`](#cond-comparison)) comparison and are deemed equal if both their string representations and data types are the same

### Example
```json
{
    "prefixes": {
        "rail": "http://example.org/ontology/rail/"
    },
    "filter": {">=": ["rail:wheelCount", 10]}
}
```
_Twins which have at least 10 wheels._


# <a name="cond-in"></a>In (any-of equality)
This operator can be used to perform multiple equality checks ([`==`](#cond-comparison)), of which any one has to match.

<pre>
{"in": [<a href="#property-path">PROPERTY_PATH</a>,  [<a href="#values">VALUE</a>, <a href="#values">VALUE</a>, ...]}
</pre>

- At least two [values](#values) must be specified.

### Example

```json
{
    "prefixes": {
        "engines": "http://example.org/ontology/engines/"
    },
    "filter": {"in": [["$feed", "rdf:type"], ["engines:DieselEngine", "engines:PetrolEngine"]]}
}
```
_Feeds of Petrol or Diesel engines._

- The above is equivalent to two individual == conditions combined with boolean logic.


## <a name="cond-has"></a>Property existence
Sometimes only the existence of a property is important (from a filtering perspective) rather than what its values are.

<pre>
{"has": <a href="#property-path">PROPERTY_PATH</a>}
</pre>


### Examples
```json
{
    "prefixes": {
        "rail": "http://example.org/ontology/rail/"
    },
    "filter": {"has": ["$feed", "rail:serviceRecord"]}
}
```
_Twins with Feeds which have at least one service record. (Maybe after each routine service of a train a new service record is added.)_

One can also use this operator to only return twins which have a spatial location (as set via Iotics API UpserTwin or UpdateTwin calls):

```json
{
    "prefixes": {
        "geo": "http://www.opengis.net/ont/geosparql#"
    },
    "filter": {"has": ["$twin", "geo:hasDefaultGeometry"]}
}
```

- The twin condition can also be written using implied twin subject (see [Property Paths](#property-path)) as `{"has": "geo:hasDefaultGeometry"}`.


## <a name="cond-spatial-nearby"></a>Spatial: Nearby
The classic search API supports [by-radius spatial filtering](https://github.com/Iotic-Labs/api/blob/55f8e8a9e8a48dffd3b5a8b526b4b3f975c4bc60/proto/iotics/api/search.proto#L62-L63). Said feature also exists in this iteration of Iotics search. (The `geo` prefix herein refers to the [GeoSPARQL namespace](http://www.opengis.net/ont/geosparql#).)
This operator matches if the given subject ([binding](#binding)) is within the specified distance from a given point (using [WGS84](https://epsg.io/4326) CSR).

<pre>
{"spatial-nearby": [<a href="#binding">BINDING</a>, [LAT, LONG, RADIUS]]}
</pre>

- `BINDING` for now can only be `$twin`
- `LAT` is the latitude of the point (in degrees WGS84, as a JSON Number)
- `LONG` is the longitude of the point (in degrees WGS84, as a JSON Number)
- `RADIUS` defines the size of the circle around the point (in kilometres, as a JSON Number)
- Subjects will be considered for spatial matching only if they have a `geo:hasDefaultGeometry / geo:asWKT` property path. (This is true for any Twins which have had their location set via `UpdateTwin` or `UpsertTwin`.)

### Example
```json
{"filter": {"spatial-nearby": ["$twin", [52.244384, 0.716356, 1.5]]}}
```
_Twins which are within 1.5 km of Bury St Edmunds, UK._


## <a name="cond-logic"></a>And/Or (Boolean logic)
Using the `or`/`and` operators allows for any/all of a given set of conditions to be satisfied, respectively.

<pre>
{LOGIC_OP: [<a href="#condition">CONDITION</a>, <a href="#condition">CONDITION</a>, ...]}
</pre>

- `LOGIC_OP` is one of: `"and"`, `"or"`
- At least two [conditions](#condition) must be specified.
- In the context of `and`, multiple conditions apply to the same `$feed` / `$input` of a twin. In other words: “Twins which have a feed/input which satisfies all of the given conditions” (as opposed to “A twin which has feeds/inputs which satisfy all of the given conditions among them”).
- There are no limits to how nested combinations of conditions can be but spaces might enforce overall condition complexity limits (which could lead to no results).

### Example
```json
{
    "prefixes": {
        "rail": "http://example.org/ontology/rail/",
        "engines": "http://example.org/ontology/engines/"
    },
    "filter": {"and": [
        {">=": [["$twin", "rail:grossWeight"], 20000]},
        {"==": [["$feed", "rdf:type"], "engines:DieselEngine"]}
    ]}
}
```
_Twins which weigh at least 20 tonnes and have diesel engine feeds._

It is also possible to combine multiple nested conditions, e.g.:
```json
{
    "prefixes": {
        "rail": "http://example.org/ontology/rail/",
        "engines": "http://example.org/ontology/engines/"
    },
    "filter": {"and": [
        {"or": [
            {">=": [["$twin", "rail:grossWeight"], 20000]},
            {"==": [["$twin", "rail:trainColour"], "green"]}
        ]},
        {"==": [["$feed", "rdf:type"], "engines:DieselEngine"]}
    ]}
}
```
_Twins which either weigh at least 20 tonnes or are green. Additionally those twins must have diesel engine feeds._

- In the context of and, multiple conditions apply to the same $feed / $input of a twin. In other words: “Twins which have a feed/input which satisfies all of the given conditions” (as opposed to “A twin which has feeds/inputs which satisfy all of the given conditions among them”).
- There are no limits to how nested combinations of conditions can be but spaces might enforce overall condition complexity limits (which would lead to no results).

## <a name="cond-not"></a>Not (inverse)
Sometimes the inverse of one or more conditions might be desired for which the `!` operator can be used.

<pre>
{"!": <a href="#condition">CONDITION</a>}
</pre>

### Example
```json
{
    "prefixes": {
        "engines": "http://example.org/ontology/engines/"
    },
    "filter": {"!": {"in": [["$twin", "rdf:type"], ["engines:DieselEngine", "engines:PetrolEngine"]]}}
}
```
_Twins other than Petrol or Diesel engines._


# <a name="property-path"></a>Property Paths
A property path defines:
- What type of property is to be matched (e.g. `http://example.org/rail/maximumCarriages`)
- Which subject should the property reference (e.g. Twin or Feed of a Twin)

Two forms are possible:

## Implied twin property by prefix
This form is useful for making filter definitions easier to read when referencing Twin properties.

```
"prefixAlias:propertyName"
```

- The subject of the match is always the Twin
- A previously registered [prefix](#prefix) **must** be referenced (here `prefixAlias`)

### Example
```json
{"filter": {"has": "rdfs:label"}}
```

## Full property path
This form allows for any subject to be referenced, not just Twins.

<pre>
[<a href="#binding">BINDING</a>, <a href="#link">LINK</a>]
</pre>
or (with implied [relative](#val-rel) link)
<pre>
[<a href="#binding">BINDING</a>, "prefixAlias:propertyName"]
</pre>

### Examples
The following two are equivalent
```json
{"filter": {"has": ["$feed", "rdfs:label"]}}

{"filter": {"has": ["$feed", {"iri": "http://www.w3.org/2000/01/rdf-schema#label"}]}}
```
_Twins which have Feeds with labels_


# <a name="binding"></a>Bindings
Sometimes it is useful to refer to an indirect relationship of a twin. This can be done using the following built-in bindings.

```
BINDING
```

- A binding (string) is recognised with its `$` prefix.
- `BINDING` can be one of:
    - `"twin"` - the Twin itself
    - `"feed"` - any Feed belonging to the Twin
    - `"input"` - any Input belonging to the Twin


# <a name="link"></a>Links
A link defines an IRI in either absolute or relative form.

```
{LINK_OP: ARGUMENTS}
```

- `LINK_OP` is one of:
    - ["`iri`"](#val-iri)
    - ["`rel`"](#val-rel)
- `ARGUMENTS` are specific to a given operator


# <a name="values"></a>Values
Filter operators (such as [comparison](#cond-comparison)) require one or more values to be specified to match against e.g. properties. Their data type can either be specified explicitly or, for a subset, implied by their JSON representation.


## <a name="val-iri"></a>IRI
This is used to refer to ontological definitions or specify absolute links to other resource.

```
{"iri": "iri-value"}
```

### Examples
```json
{"iri": "http://purl.obolibrary.org/obo/UO_0000027"}

{"iri": "urn:uuid:537944e8-cb05-4a48-9545-dae5caaa6807"}

{"iri": "did:iotics:iotRoCia9BVAaFbdfLrJujPMRmnLfB8hMN81"}
```

## <a name="val-rel"></a>REL (IRI relative to a prefix)
For readability, IRIs can also be expressed using this shorthand, assuming an applicable [prefix](#prefix) has been defined.
```
{"rel": "alias:iri-suffix"}
```


### Examples
```json
{"rel": "rail:wheelCount"}

{"rel": "rdfs:label"}

{"rel": "xsd:integer"}
```


## <a name="val-lang-str"></a>Language string
Language-aware strings must always be explicitly specified:

```
{"strlang": ["the string", "LANGUAGE_CODE"]}
```

- `LANGUAGE_CODE` must be two letter longs (see [ISO 639-1](https://en.wikipedia.org/wiki/ISO_639-1))


### Example
```json
{"strlang": ["Waschmaschinenpulver", "de"]}
```


## <a name="val-literal"></a>Literal
Any other value type falls into this category. The associated data type has to be explicitly specified either as a prefixed name:

<pre>
{"strdt": ["encoded value", <a href="#link">LINK</a>]}
</pre>
or (with implied [relative](#val-rel) link)
```
{"strdt": ["encoded value", "prefixAlias:dataType"]}
```

### Examples
```json
{"strdt": ["2022-07-14T17:00:00.000Z", "xsd:dateTime"]}

{"strdt": ["2022-07-14T17:00:00.000Z", {"rel": "xsd:dateTime"}]}

{"strdt": ["2022-07-14T17:00:00.000Z", {"iri": "http://www.w3.org/2001/XMLSchema#dateTime"}]}
```

**Note**: All of the above represent the same literal.


## <a name="values-implicit"></a>Implicit Values
The following JSON values map directly to specific data types, in the context of value definitions:

JSON                                    | Filter value type
--------------------------------------- | -----------------
`string`                                | `xsd:string`
`true`                                  | `xsd:boolean`
`false`                                 | `xsd:boolean`
`number` (without fraction / exponent)  | `xsd:integer`
`number` (with fraction / exponent)     | `xsd:decimal` / `xsd:double`

**Note**: To specify a non-integer number with a different data type, use the [Literal](#val-literal) notation (with e.g. `xsd:Decimal`).

### Examples
Each of the following pairs of implicit and explicit Values are equivalent
```json
"the string"
{"strdt": ["the string", "xsd:string"]}
```
```json
false
{"strdt": ["false", "xsd:boolean"]}
```
```json
123
{"strdt": ["123", "xsd:integer"]}
```
```json
-123.456
{"strdt": ["-123.456", "xsd:decimal"]}
```
```json
-123.456e10
{"strdt": ["-123.456e10", "xsd:double"]}
```
