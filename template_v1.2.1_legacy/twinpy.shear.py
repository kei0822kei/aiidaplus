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
wf = 'twinpy.shear'
label = "this is label"
description = "this is description"
dry_run = False
# dry_run = True
is_phonon = True
max_wallclock_seconds_relax = 100 * 3600
max_wallclock_seconds_phonon = 100 * 3600
clean_workdir = True

#----------------------
# twinpy shear settings
#----------------------
shear_conf = {
        'twinmode': '10-12',
        # 'grids': 2,
        'grids': 5,
        # 'structure_type': 'primitive'  # or 'conventional' or ''
        'is_primitive': True,  # or 'conventional' or ''
        # 'structure_type': 'conventional'  # or 'conventional' or ''
        # 'structure_type': ''  # or 'conventional' or ''
        }

#----------
# structure
#----------
# structure_pk = 4775  # Ti
# structure_pk = 11850  # Ti, glass database
structure_pk = 6836 # Ti_c, aiida database
# structure_pk = 5024 # Ti_d, aiida database
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
    'ediff': 1e-6,
    'gga': 'PS',
    'ialgo': 38,
    'lcharg': False,
    'lreal': False,
    'lwave': False,
    'npar': 4,
    'kpar': 2,
    'prec': 'Accurate',
    }

### encut
# encut = 300
encut = get_encut(potential_family=potential_family,
                  potential_mapping=potential_mapping,
                  multiply=1.3)

incar_settings['encut'] = encut

## for metal
smearing_settings = {
    'ismear': 1,
    'sigma': 0.4
    }
incar_settings.update(smearing_settings)

#---------------
# phonon_conf
#---------------

phonon_conf = {
    'distance': 0.03,
    'mesh': [18, 18, 10],
    'supercell_matrix': [2, 2, 2],
    'symmetry_tolerance': 1e-5
    }



#---------------
# relax_settings
#---------------
# volume and shape relaxation is False by default
relax_conf = {
    'algo': 'rd',  # default 'cg'
    'steps': 40,
    'convergence_absolute': False,
    'convergence_max_iterations': 3,
    # 'convergence_max_iterations': 10,
    'convergence_on': True,
    'convergence_positions': 0.01,
    # 'force_cutoff': 0.0001,
    'force_cutoff': 0.01,
    }

# 'add_structure': True is automatically set
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

#---------------
# kpoints_phonon
#---------------
### use kdensity
kpoints_phonon = {
    'mesh': None,
    'kdensity': 0.2,
    'offset': None,
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
    builder.is_phonon = Bool(is_phonon)

    # label and descriptions
    builder.metadata.label = label
    builder.metadata.description = description

    # structure
    builder.structure = load_node(structure_pk)

    # twinpy settings
    builder.shear_conf = Dict(dict=shear_conf)

    # vasp settings
    hexagonal = get_twinpy_structure_from_structure(builder.structure)
    hexagonal.set_parent(twinmode=shear_conf['twinmode'])
    hexagonal.set_is_primitive(shear_conf['is_primitive'])
    hexagonal.run()
    pmgparent = hexagonal.get_pymatgen_structure()
    kpoints_relax = get_kpoints(structure=pmgparent,
                                mesh=kpoints['mesh'],
                                kdensity=kpoints['kdensity'],
                                offset=kpoints['offset'])
    supercell = deepcopy(pmgparent)
    supercell.make_supercell(phonon_conf['supercell_matrix'])
    kpoints_ph = get_kpoints(structure=supercell,
                             mesh=kpoints_phonon['mesh'],
                             kdensity=kpoints_phonon['kdensity'],
                             offset=kpoints_phonon['offset'])
    base_settings = {
            'vasp_code': 'vasp544mpi',
            'incar_settings': incar_settings,
            'potential_family': potential_family,
            'potential_mapping': potential_mapping,
            }
    relax_settings = deepcopy(base_settings)
    relax_settings.update({
        'kpoints': {'mesh': kpoints_relax['mesh'], 'offset': kpoints_relax['offset']},
        'options': {'queue_name': queue,
                    'max_wallclock_seconds': max_wallclock_seconds_relax},
        'relax_conf': relax_conf,
        'clean_workdir': clean_workdir,
        'parser_settings': parser_settings,
        })
    phonon_settings = deepcopy(base_settings)
    phonon_settings.update({
        'kpoints': {'mesh': kpoints_ph['mesh'], 'offset': kpoints_ph['offset']},
        'options': {'queue_name': queue,
                    'max_wallclock_seconds': max_wallclock_seconds_phonon},
        'phonon_conf': phonon_conf,
        })
    builder.calculator_settings = Dict(dict={'relax': relax_settings,
                                             'phonon': phonon_settings})

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
