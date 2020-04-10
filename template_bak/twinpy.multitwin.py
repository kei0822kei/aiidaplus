#!/usr/bin/env python

import yaml
import argparse
import numpy as np
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import run, submit
from aiida.orm import load_node, Bool, Code, Dict, Float, Group, Int, Str, KpointsData, ArrayData, Dict, StructureData
from aiidaplus.utils import (get_default_potcar_mapping,
                             get_elements_from_aiidastructure,
                             get_encut,
                             get_grids_from_density)
from twinpy.crystalmaker import HexagonalTwin

def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--computer', type=str,
        default='stern', help="input computer (default:stern)'")
    parser.add_argument('--queue', type=str,
        default='', help="queue name, default None")
    parser.add_argument('--group', type=str,
        default=None, help="add nodes to specified group")
    parser.add_argument('--dry_run', action='store_true',
        help="if True, dry run")
    args = parser.parse_args()
    return args

args = get_argparse()

def get_grids_from_structure(structure, twinmode, twintype, dim,
                             density, direct_or_reciprocal):
    a = structure.lattice.a
    c = structure.lattice.c
    symbol = structure.species[0].value
    hexagonal = HexagonalTwin(a=a, c=c, twinmode=twinmode, symbol=symbol)
    twinboundary = hexagonal.get_dichromatic(twintype=twintype, dim=dim, is_complex=True)
    if direct_or_reciprocal == 'direct':
        grids = get_grids_from_density(
                twinboundary, density, 'direct')
    if direct_or_reciprocal == 'reciprocal':
        grids = get_grids_from_density(
                twinboundary, density, 'reciprocal')
    return grids

@with_dbenv()
def get_elements(pk):
    node = load_node(pk)
    elements = get_elements_from_aiidastructure(node)
    return elements

#----------------
# twinpy settings
#----------------
wf = 'twinpy.multitwins'
label = "this is label"
description = "this is description"
structure_pk = 4775
twinmode = '10-12'
twintype = 1
dim = np.array([1,1,2])
distance_threshold = 1.

#===================
### tranlation_grids
#===================
# translation_grids = np.array([5,5,1])
translation_grids = 0.2
# translation_grids = 1.5


#----------------
# vasp settings
#----------------
vasp_settings = {
        'clean_workdir': False,
        'code': 'vasp544mpi',
        }

#==========
### options
#==========
option_settings = {
        'max_wallclock_seconds': 36000,
        'tot_num_mpiprocs': 16,
        }
vasp_settings.update({'options': option_settings})

#=========
### potcar
#=========
elements = get_elements(structure_pk)
potential_family = 'PBE.54'
potential_mapping = get_default_potcar_mapping(elements)
# potential_mapping = {
#         'Na': 'Na',
#         'Cl': 'Cl'
#         }
potcar_settings = {
        'potential_family': potential_family,
        'potential_mapping': get_default_potcar_mapping(elements),
        }
vasp_settings.update({'potcar': potcar_settings})

#========
### incar
#========
incar_settings = {
    'addgrid': True,
    'ediff': 1e-6,
    'gga': 'PS',
    'ialgo': 38,
    'lcharg': False,
    'lreal': False,
    'lwave': False,
    'npar': 4,
    'prec': 'Accurate',
    }

# encut = 300
encut = get_encut(potential_family=potential_family,
                  potential_mapping=potential_mapping,
                  multiply=1.3)
incar_settings['encut'] = encut

smearing_settings = {
    'ismear': 1,
    'sigma': 0.2
    }
incar_settings.update(smearing_settings)

#==========
### kpoints
#==========
# kpoints = {
#     'mesh': [6, 6, 6],
#     'offset': [0.5, 0.5, 0.5]
#     }
kpoints = {
    'kdensity': 0.2,
    'offset': [0.5, 0.5, 0.5]
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
         group=None,
         dry_run=False):

    # group check
    if group is not None:
        check_group_existing(group)

    # computer, queue, incar
    vasp_settings.update({
            'computer': computer,
            'queue': queue,
            })
    vasp_settings.update({'incar': incar_settings})

    # twinpy settings
    workflow = WorkflowFactory(wf)
    builder = workflow.get_builder()
    builder.structure = load_node(structure_pk)
    builder.twinmode = Str(twinmode)
    builder.twintype = Int(twintype)
    dim_array = ArrayData()
    dim_array.set_array('dim', dim)
    builder.dim = dim_array
    builder.dry_run = Bool(dry_run)
    builder.distance_threshold = Float(distance_threshold)

    # label and descriptions
    builder.metadata.label = label
    builder.metadata.description = description

    # translation_grids
    if type(translation_grids) == float:
        returns = get_grids_from_structure(
                builder.structure.get_pymatgen_structure(),
                twinmode, twintype, dim, translation_grids, 'direct')
        returns[2] = 1
        trans_grids = returns
    elif len(translation_grids) == 3:
        trans_grids = translation_grids
    else:
        raise ValueError("translation_grids are not correct: %s"
                % translation_grids)
    translation_grids_array = ArrayData()
    translation_grids_array.set_array('translation_grids', trans_grids)
    builder.translation_grids = translation_grids_array

    # kpoints
    if 'kdensity' in kpoints:
        kpoints['mesh'] = get_grids_from_structure(
                builder.structure.get_pymatgen_structure(),
                twinmode, twintype, dim, kpoints['kdensity'], 'reciprocal')
        input_kpoints = {'mesh': kpoints['mesh'],
                         'offset': kpoints['offset']}
        vasp_settings.update({'kpoints': input_kpoints})

    # vasp settings
    builder.vasp_settings = Dict(dict=vasp_settings)

    # submit
    future = submit(workflow, **builder)
    print(future)
    print('Running workchain with pk={}'.format(future.pk))

    # add group
    grp = Group.get(label=group)
    running_node = load_node(future.pk)
    grp.add_nodes(running_node)
    print("pk {} is added to group: {}".format(future.pk, group))

if __name__ == '__main__':
    main(computer=args.computer,
         queue=args.queue,
         group=args.group,
         dry_run=args.dry_run)
