#!/usr/bin/env python

import yaml
import argparse
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import run, submit
from aiida.orm import (load_node, Bool, Code, Dict, Float,
                       Group, Int, Str, KpointsData)
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
wf = 'twinpy.shear'
max_wallclock_seconds = 36000
label = "this is label"
description = "this is description"
# dry_run = True
dry_run = False

#----------------------
# twinpy shear settings
#----------------------
twinmode = '10-12'
# grids = 5
grids = 2

#----------
# structure
#----------
structure_pk = 4775  # Ti
elements = get_elements(structure_pk)

#-------
# potcar
#-------
potential_family = 'PBE.54'
potential_mapping = get_default_potcar_mapping(elements)
# potential_mapping = {
#         'Na': 'Na',
#         'Cl': 'Cl'
#         }

#------
# incar
#------
### base setting
incar_settings = {
    'addgrid': True,
    # 'ediff': 1e-6,
    'ediff': 1e-2,
    'gga': 'PS',
    'ialgo': 38,
    'lcharg': False,
    'lreal': False,
    'lwave': False,
    'npar': 4,
    'prec': 'Accurate',
    }

### encut
# encut = 300
encut = get_encut(potential_family=potential_family,
                  potential_mapping=potential_mapping,
                  multiply=1.3)

incar_settings['encut'] = encut

### metal or not metal
##### metal
smearing_settings = {
    'ismear': 1,
    'sigma': 0.2
    }
##### not metal
# smearing_settings = {
#     'ismear': 0,
#     'sigma': 0.01
#     }

incar_settings.update(smearing_settings)

#---------------
# relax_settings
#---------------
relax_conf = {
    'algo': 'rd',  # you can also choose 'cg' (default)
    'steps': 40,
    'convergence_absolute': False,
    # 'convergence_max_iterations': 3,
    'convergence_max_iterations': 1,
    'convergence_on': True,
    'convergence_positions': 0.01,
    # 'force_cutoff': 0.0001,
    'force_cutoff': 0.01,
    }

#--------
# kpoints
#--------
# kpoints = {
#     'mesh': [6, 6, 6],
#     'kdensity': None,
#     'offset': [0.5, 0.5, 0.5]
#     # 'offset': [0.5, 0.5, 0.5]
#     }
### not use kdensity
# kpoints = {
#     'mesh': [6, 6, 6],
#     'kdensity': None,
#     'offset': None
#     # 'offset': [0.5, 0.5, 0.5]
#     }
### use kdensity
kpoints = {
    'mesh': None,
    'kdensity': 0.2,
    'offset': None
    # 'offset': [0.5, 0.5, 0.5]
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
    builder.vaspcode = Str('vasp544mpi')
    builder.clean_workdir = Bool(False)
    builder.queue = Str(queue)
    builder.dry_run = Bool(dry_run)

    # label and descriptions
    builder.metadata.label = label
    builder.metadata.description = description


    # structure
    builder.structure = load_node(structure_pk)

    # twinpy shear settings
    builder.twinmode = Str(twinmode)
    builder.grids = Int(grids)

    # incar
    builder.incar_settings = Dict(dict=incar_settings)

    # relax
    builder.relax_conf = Dict(dict=relax_conf)

    # kpoints
    kpt = KpointsData()
    mesh, offset = get_kpoints(structure=builder.structure.get_pymatgen(),
                               mesh=kpoints['mesh'],
                               kdensity=kpoints['kdensity'],
                               offset=kpoints['offset'])
    kpt.set_kpoints_mesh(mesh, offset=offset)
    builder.kpoints = kpt


    # potcar
    builder.potential_family = Str(potential_family)
    builder.potential_mapping = Dict(dict=potential_mapping)

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
