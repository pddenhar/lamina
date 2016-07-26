#!/usr/bin/python

from __future__ import print_function
import sys
import inspect
from functools import wraps
import os, shutil, glob
import logging
import FSops

logging.basicConfig(format='%(levelname)s:%(filename)s:%(lineno)s %(message)s',level=logging.DEBUG)
LAMINA_DIRECTORY = "/var/lib/lamina/"
LAYERS_DIRECTORY = LAMINA_DIRECTORY + "layers/"
MOUNT_DIRECTORY = LAMINA_DIRECTORY + "mounts/"

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
    if len(layer_children) != 0:
        if (raw_input("Layer {0} has {1} children, are you sure you want to delete it? (y/n) ".format(name,len(layer_children))) != 'y'):
            return False
    for child in layer_children:
        if delete(child) == False:
            return False

    layerdir = LAYERS_DIRECTORY+name
    manifest_path = LAYERS_DIRECTORY+name+".parents"
    if not os.path.exists(layerdir):
        logging.error("Layer to be deleted does not exist, aborting.")
        return
    shutil.rmtree(layerdir)
    os.remove(manifest_path)
    logging.info("Deleted "+name)

@kwargify
def list_layers():
    def printChildren(name, indent):
        print(' '*indent, end="")
        print(name)
        for child in children(name):
            printChildren(child, indent+2)
    
    manifests = glob.glob(LAYERS_DIRECTORY+"*.parents")
    for manifest in manifests:
        with open(manifest, 'r') as myfile:
            data=myfile.read().replace('\n', '').strip()
            if(len(data)==0):
                printChildren(os.path.splitext(os.path.basename(manifest))[0],0)

@kwargify
def mount_layer(name):
    mount_path=FSops.mount_layer(name, LAYERS_DIRECTORY, "/mnt/")
    print("Layer mounted at {0}".format(mount_path))

@kwargify
def unmount_layer(name):
    FSops.unmount_layer(name)

@kwargify
def run_command(name, command, args):
    mount_location = FSops.prep_chroot(name, LAYERS_DIRECTORY, MOUNT_DIRECTORY)
    chroot_command = "chroot {0} {1} {2}".format(mount_location, command, " ".join(args))
    os.system(chroot_command)
    FSops.cleanup_chroot(name)
    
        

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
    parser_list.set_defaults(func=list_layers)

    parser_run = subparsers.add_parser('run', help='Run a command on a lamina layer')
    parser_run.add_argument('name', help='lamina layer name to run command in')
    parser_run.add_argument('command', help='command to run')
    parser_run.add_argument('args', help='arguments for command', nargs=argparse.REMAINDER)
    parser_run.set_defaults(func=run_command)

    parser_mount = subparsers.add_parser('mount', help='Mount a lamina layer so that you can modify it directly')
    parser_mount.add_argument('name', help='lamina layer name to mount')
    parser_mount.set_defaults(func=mount_layer)

    parser_unmount = subparsers.add_parser('unmount', help='Unmount a lamina layer')
    parser_unmount.add_argument('name', help='lamina layer name to unmount')
    parser_unmount.set_defaults(func=unmount_layer)

    args = parser.parse_args()
    args.func.kwargified(args)
