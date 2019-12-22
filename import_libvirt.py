#!/usr/bin/env python3

"""
Usage:
  import_libvirt.py [options] <qemu_image>

Options:
  -h --help                     Show this screen.
  -q=PATH, --qemu=PATH          Path to custom QEMU binary
  --open-vnc                    Open VNC on all interfaces (0.0.0.0)
  -u=URI, --uri=URI             Specify libvirt's URI [default: qemu:///system]
  -p=POOL, --pool=POOL          Specify pool name [default: default]
  -k=PREFIX, --prefix=PREFIX    Specify VM prefix
"""

import os
import sys
import logging
import shutil
import xml.etree.ElementTree as tree

import libvirt
from docopt import docopt

PACKER_OUTPUT_DIR = 'output-qemu'
SNAPSHOT_XML = """
<domainsnapshot>
    <name>base</name>
</domainsnapshot>
"""

def prepare_domain_xml(domain_name, qemu_bin_path, nitro_image_path, open_vnc):
    with open('template_domain.xml') as templ:
        domain_xml = templ.read()
        domain_xml = domain_xml.format(domain_name, qemu_bin_path,
                                       nitro_image_path)
        root = tree.fromstring(domain_xml)
        if open_vnc:
            # search for graphics element
            graphics_elem = root.findall("./devices/graphics")[0]
            graphics_elem.attrib['listen'] = '0.0.0.0'
        domain_xml = tree.tostring(root).decode()
        return domain_xml
    return None

def main(args):
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    qemu_image = args['<qemu_image>']
    open_vnc = args['--open-vnc']
    libvirt_uri = args['--uri']
    pool_name = args['--pool']
    prefix = args['--prefix']
    if not prefix:
        prefix = ""

    con = libvirt.open(libvirt_uri)
    script_dir = os.path.dirname(os.path.realpath(__file__))
    storage_path = os.path.join(script_dir, '..', 'images')
    # check for storage pool
    try:
        storage = con.storagePoolLookupByName(pool_name)
    except libvirt.libvirtError:
        # build pool xml
        path_elem = tree.Element('path')
        path_elem.text = storage_path
        target_elem = tree.Element('target')
        target_elem.append(path_elem)
        name_elem = tree.Element('name')
        name_elem.text = pool_name
        pool_elem = tree.Element('pool', attrib={'type': 'dir'})
        pool_elem.append(name_elem)
        pool_elem.append(target_elem)
        pool_xml = tree.tostring(pool_elem).decode('utf-8')
        # define it
        storage = con.storagePoolDefineXML(pool_xml)
        storage.setAutostart(True)
    # create dir
    os.makedirs(storage_path, exist_ok=True)
    # make sure storage is running
    if not storage.isActive():
        storage.create()
    # check if domain is already defined
    image_name = os.path.basename(qemu_image)
    domain_name = '{}{}'.format(prefix, image_name)
    try:
        domain = con.lookupByName(domain_name)
    except libvirt.libvirtError:
        # default system qemu
        qemu_bin_path = shutil.which('qemu-system-x86_64')
        # set custom qemu if needed
        if args['--qemu']:
            qemu_bin_path = args['--qemu']
        # move image to our pool
        nitro_image_path = os.path.join(storage_path, '{}.qcow2'.format(image_name))
        shutil.move(qemu_image, nitro_image_path)
        domain_xml = prepare_domain_xml(domain_name, qemu_bin_path, nitro_image_path,
                                        open_vnc)
        con.defineXML(domain_xml)
        logging.info('Domain {} defined.'.format(domain_name))
        domain = con.lookupByName(domain_name)
        # take base snapshot
        domain.snapshotCreateXML(SNAPSHOT_XML)
        # remove output-qemu
        output_qemu_path = os.path.join(script_dir, PACKER_OUTPUT_DIR)
        shutil.rmtree(output_qemu_path)
    else:
        logging.info('Domain {} already defined'.format(domain_name))



if __name__ == '__main__':
    args = docopt(__doc__)
    logging.basicConfig(level=logging.DEBUG)
    main(args)
