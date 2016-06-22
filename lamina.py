#!/usr/bin/python

from __future__ import print_function
import sys
import inspect
from functools import wraps

# Add a .kwargified attribute to a method that accepts an argparse namespace as the kwargs for a method
def kwargify(method):
    @wraps(method)
    def _safe(obj):
        stripped = {key: value for key, value in vars(obj).items() if key in inspect.getargspec(method).args}
        return method(**stripped)
    method.kwargified = _safe
    return method

@kwargify
def create(name=""):
    print(name)

@kwargify
def delete(name=""):
    print("del"+name)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create and deploy overlaid filesystems to bare metal devices, similar to how Docker images work for containers.")
    #parser.add_argument("action", choices = ["create"], help = "lamina action to run")
    subparsers = parser.add_subparsers(title="lamina actions", help='lamina action to run')

    parser_create = subparsers.add_parser('create', help='create a lamina base layer image with no contents')
    parser_create.add_argument('name', help='lamina image name to create')
    parser_create.set_defaults(func=create)

    parser_delete = subparsers.add_parser('delete', help='delete a lamina image')
    parser_delete.add_argument('name', help='lamina image name to delete')

    args = parser.parse_args()
    args.func.kwargified(args)