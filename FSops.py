#!/usr/bin/python

from __future__ import print_function
from subprocess import call
import os

LAMINA_MOUNT_LABEL_PREFIX = "lamina-aufs-"

def mount_layer(name, layers_dir, mount_location):
  # dirs=<top>=<opts>:<next_down>=<next_opts>
  #mount_command = "mount -t aufs -o br:${ROOT_RW}:${LATEST_IMAGE}=ro+wh:${NEXT_IAMGE}=RO+WH aufs-root ${rootmnt}"
  layerdir = layers_dir+name
  manifest_path = layers_dir+name+".parents"

  aufs_branches = []
  #manifest files are in the order bottom layer->..->nearest parent
  with open(manifest_path, 'r') as manifest:
    for line in manifest:
      aufs_branches.append("{0}/=ro+wh".format(layers_dir + line.strip()))
  aufs_branches.append("{0}/=rw".format(layers_dir + name))
  #need the layers in order from top->bottom
  aufs_branches.reverse()
  aufs_mount_string = "br:" + ":".join(aufs_branches)
  mount_path = mount_location+name+"/"
  mount_label = LAMINA_MOUNT_LABEL_PREFIX+name
  if not os.path.exists(mount_path):
    os.makedirs(mount_path)

  call(["mount", "-t", "aufs", "-o", aufs_mount_string, mount_label, mount_path])
  return mount_path

def unmount_layer(name):
  mount_label = LAMINA_MOUNT_LABEL_PREFIX+name
  call(["umount", mount_label])

def prep_chroot(name, layers_dir, mount_location):
  mount_location = mount_layer(name, layers_dir, mount_location)
  for f in ["proc", "sys", "dev"]:
    os.system("sudo mount --bind /{0} {1}{0}".format(f,mount_location))
  return mount_location

def cleanup_chroot(name):
  unmount_layer(name)