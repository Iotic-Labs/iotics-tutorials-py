import sys
from typing import Optional

from requests import Response, request


def make_api_call(
    method: str,
    endpoint: str,
    headers: Optional[dict] = None,
    payload: Optional[dict] = None,
) -> dict:
    try:
        req_resp: Response = request(
            method=method, url=endpoint, headers=headers, json=payload
        )
        req_resp.raise_for_status()
        response: dict = req_resp.json()
    except Exception as ex:
        print("Getting error", ex)
        sys.exit(1)

    return response


def print_property_rest(prop: dict, formatting=""):
    """This method will be used to print in a nice way
    the list of Properties of Twin, Feeds and Inputs."""

    property_key = prop.get("key")
    print(f"{formatting}-  Key: {property_key}")
    property_uri: dict = prop.get("uriValue")
    property_lang_literal: dict = prop.get("langLiteralValue")
    property_string_literal: dict = prop.get("stringLiteralValue")
    property_literal: dict = prop.get("literalValue")
    if property_uri:
        print(f"{formatting}   URI Value:", property_uri.get("value"))
    if property_lang_literal:
        print(f"{formatting}   Lang Literal Value:", property_lang_literal.get("value"))
        print(f"{formatting}   Lang:", property_lang_literal.get("lang"))
    if property_string_literal:
        print(
            f"{formatting}   String Literal Value:",
            property_string_literal.get("value"),
        )
    if property_literal:
        print(f"{formatting}   Literal Value:", property_literal.get("value"))
        print(f"{formatting}   Datatype:", property_literal.get("dataType"))


def print_property_grpc(prop, formatting=""):
    """This method will be used to print in a nice way
    the list of Properties of Twin, Feeds and Inputs."""

    property_key = prop.key
    print(f"{formatting}-  Key: {property_key}")
    property_uri = prop.uriValue.value
    property_lang_literal_value = prop.langLiteralValue.value
    property_lang_literal_lang = prop.langLiteralValue.lang
    property_string_literal_value = prop.stringLiteralValue.value
    property_literal_value = prop.literalValue.value
    property_literal_datatype = prop.literalValue.dataType
    if property_uri:
        print(f"{formatting}   URI Value:", property_uri)
    if property_lang_literal_value:
        print(f"{formatting}   Lang Literal Value:", property_lang_literal_value)
    if property_lang_literal_lang:
        print(f"{formatting}   Lang:", property_lang_literal_lang)
    if property_string_literal_value:
        print(f"{formatting}   String Literal Value:", property_string_literal_value)
    if property_literal_value:
        print(f"{formatting}   Literal Value:", property_literal_value)
    if property_literal_datatype:
        print(f"{formatting}   Datatype:", property_literal_datatype)


def print_value_rest(value: dict, formatting=""):
    value_label = value.get("label")
    value_comment = value.get("comment")
    value_unit = value.get("unit")
    value_datatype = value.get("dataType")

    print(f"{formatting}-  Label:", value_label)
    print(f"{formatting}   Comment:", value_comment)
    print(f"{formatting}   Unit:", value_unit)
    print(f"{formatting}   Datatype:", value_datatype)


def print_value_grpc(value: dict, formatting=""):
    value_label = value.get("label")
    value_comment = value.get("comment")
    value_unit = value.get("unit")
    value_datatype = value.get("dataType")

    print(f"{formatting}-  Label:", value_label)
    print(f"{formatting}   Comment:", value_comment)
    print(f"{formatting}   Unit:", value_unit)
    print(f"{formatting}   Datatype:", value_datatype)
