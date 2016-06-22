#!/usr/bin/python

from __future__ import print_function
import sys
import inspect
from functools import wraps
import os, shutil, glob
import logging

logging.basicConfig(format='%(levelname)s:%(filename)s:%(lineno)s %(message)s',level=logging.DEBUG)
LAMINA_DIRECTORY = "/var/lib/lamina/"
LAYERS_DIRECTORY = LAMINA_DIRECTORY + "layers/"

"""Add a .kwargified attribute to a method that accepts an argparse namespace as the kwargs for a method"""
def kwargify(method):
    @wraps(method)
    def _safe(obj):
        stripped = {key: value for key, value in vars(obj).items() if key in inspect.getargspec(method).args}
        return method(**stripped)
    method.kwargified = _safe
    return method

@kwargify
def create(name, parent=None):
    layerdir = LAYERS_DIRECTORY+name
    manifest_path = LAYERS_DIRECTORY+name+".parents"

    if os.path.exists(layerdir):
        logging.error("Layer already exists, aborting.")
        return

    if parent != None:
        parent_manifest_path = LAYERS_DIRECTORY+parent+".parents"
        if not os.path.isfile(parent_manifest_path):
            logging.error("Parent layer is missing, aborting.")
            return
        #copy the parent's manifest so that we can append to it
        shutil.copyfile(parent_manifest_path, manifest_path)

    os.makedirs(layerdir)
    logging.info("Created "+layerdir)

    with open(manifest_path, "a") as manifest_file:
        if parent!=None:
            print("{0}".format(parent), file=manifest_file)
        else:
            print("", file=manifest_file, end="")

@kwargify
def delete(name):
    layer_children = children(name)
    for child in layer_children:
        delete(child)

    layerdir = LAYERS_DIRECTORY+name
    manifest_path = LAYERS_DIRECTORY+name+".parents"
    if not os.path.exists(layerdir):
        logging.error("Layer to be deleted does not exist, aborting.")
        return
    shutil.rmtree(layerdir)
    os.remove(manifest_path)
    logging.info("Deleted "+name)

@kwargify
def list_images():
    manifests = glob.glob(LAYERS_DIRECTORY+"*.parents")
    print(manifests)

"""Return a list of direct children for layer name"""
def children(name):
    manifests = glob.glob(LAYERS_DIRECTORY+"*.parents")
    children = []
    for manifest in manifests:
        with open(manifest) as f:
            last = None
            # get last line of file, or closest ancestor for a layer
            for last in (line.rstrip(' \n') for line in f):
                pass
            if last != None and last==name:
                children.append(os.path.splitext(os.path.basename(manifest))[0])
    return children

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create and deploy overlaid filesystems to bare metal devices, similar to how Docker images work for containers.")
    #parser.add_argument("action", choices = ["create"], help = "lamina action to run")
    subparsers = parser.add_subparsers(title="lamina actions", help='lamina action to run')

    parser_create = subparsers.add_parser('create', help='Create a new uncommited lamina layer with no contents')
    parser_create.add_argument('parent', default=None, nargs='?', help='If no parent is specified, layer will be considered a base layer. Parent layer must be a comitted layer.')
    parser_create.add_argument('name', help='lamina layer name to create')
    parser_create.set_defaults(func=create)

    parser_delete = subparsers.add_parser('delete', help='Delete a lamina layer and all layers that depend on it')
    parser_delete.add_argument('name', help='lamina layer name to delete')
    parser_delete.set_defaults(func=delete)

    parser_list = subparsers.add_parser('list', help='List all lamina layers')
    parser_list.set_defaults(func=list_images)

    args = parser.parse_args()
    args.func.kwargified(args)