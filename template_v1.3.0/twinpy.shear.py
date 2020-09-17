#!/usr/bin/env python

import argparse
from copy import deepcopy
from aiida.plugins import WorkflowFactory
from aiida.engine import submit
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm import load_node, Bool, Dict, Group, Str
from aiidaplus.utils import (get_default_potcar_mapping,
                             get_elements_from_aiidastructure,
                             get_encut)


def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--computer',
                        type=str,
                        default='stern',
                        help="input computer (default:stern)'")
    parser.add_argument('--queue',
                        type=str,
                        default='',
                        help="queue name, default None")
    parser.add_argument('--group',
                        type=str,
                        default=None,
                        help="add nodes to specified group")
    parser.add_argument('--label',
                        type=str,
                        default=None,
                        help="set label")
    args = parser.parse_args()
    return args


args = get_argparse()


@with_dbenv()
def get_elements(pk):
    node = load_node(pk)
    elements = get_elements_from_aiidastructure(node)
    return elements


# ---------------
# common settings
# ---------------
wf = 'twinpy.shear'
label = "this is label"
description = "this is description"
dry_run = False
# dry_run = True
is_phonon = True
max_wallclock_seconds_relax = 100 * 3600
max_wallclock_seconds_phonon = 1000 * 3600
clean_workdir = True
vasp_code = 'vasp544mpi'


# ---------------------
# twinpy shear settings
# ---------------------
shear_conf = {
        'twinmode': '10-12',
        'grids': 5,
        }


# ---------
# structure
# ---------
# structure_pk = 11850  # Ti, glass database
structure_pk = 6836     # Ti_c, aiida database
# structure_pk = 5024   # Ti_d, aiida database
elements = get_elements(structure_pk)


# ------
# potcar
# ------
potential_family = 'PBE.54'
potential_mapping = get_default_potcar_mapping(elements)
# potential_mapping = {
#         'Na': 'Na',
#         'Cl': 'Cl'
#         }


# -----
# incar
# -----

# ============
# base setting
# ============
incar_settings = {
    'addgrid': True,
    'ediff': 1e-8,
    'gga': 'PS',
    'ialgo': 38,
    'lcharg': False,
    'lreal': False,
    'lwave': False,
    'npar': 4,
    'prec': 'Accurate',
    }

# =====
# encut
# =====
encut = 375
# encut = get_encut(potential_family=potential_family,
#                   potential_mapping=potential_mapping,
#                   multiply=1.3)

incar_settings['encut'] = encut

# =====
# smear
# =====
smearing_settings = {
    'ismear': 1,
    'sigma': 0.4
    }
incar_settings.update(smearing_settings)


# -----------
# phonon_conf
# -----------
phonon_conf = {
    'distance': 0.03,
    'mesh': [18, 18, 10],
    # 'supercell_matrix': [4, 4, 3],
    'supercell_matrix': [2, 2, 2],
    'symmetry_tolerance': 1e-5
    }


# --------------
# relax_settings
# --------------
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
    'force_cutoff': 1e-7,
    }

# 'add_structure': True is automatically set
parser_settings = {
    'add_misc': True,
    'add_kpoints': True,
    'add_energies': True,
    'add_forces': True,
    'add_stress': True,

    # +++++++++++++++++++++++++++++++++++++++
    # before activate parameters below
    # always chech whether is works
    # detail see parser/vasp.py in aiida-vasp
    # +++++++++++++++++++++++++++++++++++++++

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


# -------
# kpoints
# -------
kpoints = {
    'mesh': [8, 8, 6],
    'offset': [0., 0., 0.5],
    }

kpoints_phonon = {
    'mesh': [2, 2, 2],
    'offset': [0., 0., 0.5],
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
         cmd_label=None):

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
    if cmd_label is None:
        builder.metadata.label = label
    else:
        builder.metadata.label = cmd_label
    builder.metadata.description = description

    # structure
    builder.structure = load_node(structure_pk)

    # twinpy settings
    builder.shear_conf = Dict(dict=shear_conf)

    # vasp settings
    base_settings = {
            'vasp_code': vasp_code,
            'incar_settings': incar_settings,
            'potential_family': potential_family,
            'potential_mapping': potential_mapping,
            }
    relax_settings = deepcopy(base_settings)
    relax_settings.update({
        'kpoints': kpoints,
        'options': {'queue_name': queue,
                    'max_wallclock_seconds': max_wallclock_seconds_relax},
        'relax_conf': relax_conf,
        'clean_workdir': clean_workdir,
        'parser_settings': parser_settings,
        })
    phonon_settings = deepcopy(base_settings)
    phonon_settings.update({
        'kpoints': kpoints_phonon,
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
         group=args.group,
         cmd_label=args.label)
