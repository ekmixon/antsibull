# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""General functions for working with python collections and classes for new data types."""

import typing as t
from collections.abc import Container, Mapping, Sequence, Set

from ..vendored.collections import ImmutableDict


def is_sequence(obj: t.Any, include_string: bool = False) -> bool:
    """
    Return whether ``obj`` is a :python:obj:`collections.abc.Sequence`.

    You often want to know if a variable refers to a Sequence container but treat strings as being
    scalars instead of being Sequences.  This function allows you to do that.

    :arg obj: The object to test to see if it is a Sequence.
    :kwarg include_string: When False, strings are treated as not being a Sequence.  When True,
        they are.
    :returns: True if the object is a :python:obj:`collections.abc.Sequence`, False if it is not.
        Excludes strings from being a type of Sequence if ``include_string`` is False.
    """
    if isinstance(obj, (str, bytes)) and not include_string:
        return False
    return isinstance(obj, Sequence)


def compare_all_but(dict_a: t.Mapping, dict_b: t.Mapping,
                    keys_to_ignore: t.Optional[t.Iterable] = None) -> bool:
    """
    Compare two dictionaries, with the possibility to ignore some fields.

    :arg dict_a: First dictionary to compare
    :arg dict_b: Second dictionary to compare
    :kwarg keys_to_ignore: An iterable of keys whose values in the dictionaries will not be
        compared.
    :returns: True if the dictionaries have matching values for all of the keys which were not
        ignored.  False otherwise.
    """
    if keys_to_ignore is None:
        return dict_a == dict_b

    if not isinstance(keys_to_ignore, Set):
        keys_to_ignore = frozenset(keys_to_ignore)

    length_a = len(frozenset(dict_a.keys()) - keys_to_ignore)
    length_b = len(frozenset(dict_b.keys()) - keys_to_ignore)

    if length_a != length_b:
        return False

    sentinel = object()

    return all(
        value == dict_b.get(key, sentinel)
        for key, value in (
            (k, v) for k, v in dict_a.items() if k not in keys_to_ignore
        )
    )


def _make_contained_containers_immutable(obj):
    """
    Make contained containers into immutable containers.

    This is a helper for :func:`_make_immutable`.  It takes an iterable container and turns all
    values inside of it into an immutable container.  Be careful what containers you pass in.
    Mappings, for instance, will be processed without error but the results are likely not what you
    want because Mappings have both a key and a value.
    """
    temp_list = []
    for value in obj:
        if isinstance(value, Container):
            value = _make_immutable(value)
        temp_list.append(value)
    return temp_list


def _make_immutable(obj: t.Any) -> t.Any:
    """Recursively convert a container and objects inside of it into immutable data types."""
    if isinstance(obj, (str, bytes)):
        # Strings first because they are also sequences
        return obj

    if isinstance(obj, Mapping):
        temp_dict = {}
        for key, value in obj.items():
            if isinstance(value, Container):
                value = _make_immutable(value)
            temp_dict[key] = value
        return ImmutableDict(temp_dict)

    if isinstance(obj, Set):
        temp_sequence = _make_contained_containers_immutable(obj)
        return frozenset(temp_sequence)

    if isinstance(obj, Sequence):
        temp_sequence = _make_contained_containers_immutable(obj)
        return tuple(temp_sequence)

    return obj


class ContextDict(ImmutableDict):
    def __init__(self, *args, **kwargs) -> None:
        tmp_dict = (
            args[0]
            if not kwargs and len(args) == 1 and isinstance(args[0], Mapping)
            else dict(*args, **kwargs)
        )

        toplevel = {key: _make_immutable(value) for key, value in tmp_dict.items()}
        super().__init__(toplevel)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_and_convert

    @classmethod
    def validate_and_convert(cls, value: t.Mapping) -> 'ContextDict':
        return value if isinstance(value, ContextDict) else cls(value)
