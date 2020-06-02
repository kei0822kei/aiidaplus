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
# label = "this is label"
label = "k886 s443 r1.0 modulation"
description = "this is description"
dry_run = False
# dry_run = True
max_wallclock_seconds = 100 * 3600
# clean_workdir = True
clean_workdir = False

#---------------------------
# twinpy modulation settings
#---------------------------
# each set is [q-point, band index (int), amplitude (float), phase (float)]
# band index start from 0 not 1
# phase is degree
phonon_pk = 21106  # 10-12 shear ratio 1.0
dimension = np.array([[ 0, 2,-2],
                      [-1, 1,-1],
                      [ 0, 1, 1]])
qpoints = [[-0.5,0.5,0]]
band_index = 0
phase_factors = [0., 90., 180., 270.]
natoms = 8
mass = 47.8
amplitudes = np.array([0.1, 0.2, 0.3]) * np.sqrt(natoms * mass)
phonon_modes = []
for qpoint in qpoints:
    for phase_factor in phase_factors:
        for amplitude in amplitudes:
            phonon_modes.append([qpoint, band_index, amplitude, phase_factor ])
# ISIF is set 2 automatically
incar_update_settings = {
        'nsw': 60,
        'ibrion': 2,
        'ediffg': 1e-4,
        }
parser_settings = {
    'add_misc': True,
    'add_kpoints': True,
    'add_energies': True,
    'add_forces': True,
    'add_stress': True,
    'add_structure': True,

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

kpoints = {
    'mesh': [10,4,2],
    'offset': [0.5,0.5,0.5],
    }

modulation_conf = {
        'phonon_pk': phonon_pk,
        'phonon_modes': phonon_modes,
        'dimension': dimension,
        'incar_update_settings': incar_update_settings,
        'clean_workdir': clean_workdir,
        'parser_settings': parser_settings,
        'kpoints': kpoints
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
    modulation_conf.update({'queue': queue})
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
