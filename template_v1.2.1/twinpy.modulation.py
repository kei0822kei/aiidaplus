#!/usr/bin/env python

import yaml
import argparse
import numpy as np
from copy import deepcopy
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import run, submit
from aiida.orm import (load_node, Bool, Code, Dict, Float,
                       Group, Int, Str, KpointsData)
from aiida_twinpy.common.structure import get_twinpy_structure_from_structure
from aiidaplus.utils import (get_kpoints,
                             get_default_potcar_mapping,
                             get_elements_from_aiidastructure,
                             get_encut)

def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--computer', type=str,
        default='stern', help="input computer (default:stern)'")
    parser.add_argument('--queue', type=str,
        default='', help="queue name, default None")
    parser.add_argument('--group', type=str,
        default=None, help="add nodes to specified group")
    args = parser.parse_args()
    return args

args = get_argparse()

@with_dbenv()
def get_elements(pk):
    node = load_node(pk)
    elements = get_elements_from_aiidastructure(node)
    return elements

#----------------
# common settings
#----------------
wf = 'twinpy.modulation'
label = "this is label"
description = "this is description"
dry_run = False
# dry_run = True
max_wallclock_seconds = 100 * 3600
clean_workdir = True

#---------------------------
# twinpy modulation settings
#---------------------------
# each set is [q-point, band index (int), amplitude (float), phase (float)]
# band index start from 0 not 1
# phase is degree
phonon_pk = 1
phonon_modes = [
                [[0,0,0], 1, 0.2, 0.],
               ]
# ISIF is set 2 automatically
incar_update_settings = {
        'nsw': 20,
        'ibrion': 2,
        'ediffg': 1e-4,
        }
parser_settings = {
    'add_misc': True,
    'add_kpoints': True,
    'add_energies': True,
    'add_forces': True,
    'add_stress': True,

    ### before activate parameters below
    ### always chech whether is works
    ### detail see parser/vasp.py in aiida-vasp

    # 'add_dynmat': True,
    # 'add_hessian': True,
    # 'add_poscar-structure': True,
    # 'add_trajectory': True,
    # 'add_bands': False,
    # 'add_dos': False,
    # 'add_projectors': True,
    # 'add_born_charges': False,
    # 'add_chgcar': False,
    # 'add_wavecar': False,
}

modulation_conf = {
        'phonon_pk': phonon_pk,
        'phonon_modes': phonon_modes,
        'incar_update_settings': incar_update_settings,
        'clean_workdir': True,
        'parser_settings': parser_settings,
        }

def check_group_existing(group):
    print("------------------------------------------")
    print("check group '%s' exists" % group)
    print("------------------------------------------")
    Group.get(label=group)
    print("OK\n")

@with_dbenv()
def main(computer,
         queue='',
         group=None):

    # group check
    if group is not None:
        check_group_existing(group)

    # common settings
    workflow = WorkflowFactory(wf)
    builder = workflow.get_builder()
    builder.computer = Str(computer)
    builder.dry_run = Bool(dry_run)

    # label and descriptions
    builder.metadata.label = label
    builder.metadata.description = description

    # twinpy settings
    builder.modulation_conf = Dict(dict=modulation_conf)

    # submit
    future = submit(builder)
    print(future)
    print('Running workchain with pk={}'.format(future.pk))

    # add group
    if group is not None:
        grp = Group.get(label=group)
        running_node = load_node(future.pk)
        grp.add_nodes(running_node)
        print("pk {} is added to group: {}".format(future.pk, group))

if __name__ == '__main__':
    main(computer=args.computer,
         queue=args.queue,
         group=args.group)
