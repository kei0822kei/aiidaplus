#!/usr/bin/env python

import argparse
from copy import deepcopy
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.engine import submit
from aiida.orm import (load_node, Dict,
                       Group, Int, Str)
from aiidaplus.get_data import get_relax_data


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

# ----------
# relax data
# ----------
relax_pk = 255907  # aiida Ti
# relax_pk = 255939  # aiida Mg
data = get_relax_data(relax_pk)


# ---------------
# common settings
# ---------------
wf = 'twinpy.twinboundary_relax'
label = "twinpy twinboundary relax calc using relax result (pk: {})".format(
        relax_pk)
description = label
max_wallclock_seconds = 100 * 3600
clean_workdir = True


# ---------
# structure
# ---------
structure_pk = data['final_structure_pk']


# ------
# potcar
# ------
potential_family = data['steps']['step_00']['potential_family']
potential_mapping = data['steps']['step_00']['potential_mapping']


# -----
# incar
# -----
incar_settings = data['steps']['step_00']['incar']
incar_settings['ediff'] = 1e-07
del incar_settings['relax']


# --------------
# relax settings
# --------------
relax_conf = {
    'algo': 'rd',  # default 'cg'
    'steps': 20,
    'positions': True,
    'volume': False,
    'shape': False,
    'convergence_absolute': False,
    'convergence_max_iterations': 2,
    'convergence_on': True,
    'convergence_positions': 0.1,
    'force_cutoff': 1e-8,
    }


# ---------------
# parser settings
# ---------------
# -- 'add_structure': True is automatically set
parser_settings = {
    'add_misc': True,
    'add_kpoints': True,
    'add_energies': True,
    'add_forces': True,
    'add_stress': True,

    # -- before activate parameters below
    # -- always chech whether is works
    # -- detail see parser/vasp.py in aiida-vasp

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
    # 'mesh': ['check carefully'],
    'mesh': [8, 2, 4],
    'offset': [0.5, 0.5, 0.5]
    }


# ---------------------
# twinpy shear settings
# ---------------------
twinboundary_conf = {
    'twinmode': '10-12',
    'twintype': 1,
    'layers': 4,
    'delta': 0.06,
    'xshift': 0.,
    'yshift': 0.,
    'shear_strain_ratio': 0.,
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

    # label and descriptions
    if cmd_label is None:
        builder.metadata.label = label
    else:
        builder.metadata.label = cmd_label
    builder.metadata.description = description

    # structure
    builder.structure = load_node(structure_pk)

    # twinpy settings
    builder.twinboundary_conf = Dict(dict=twinboundary_conf)

    # vasp settings
    base_settings = {
            'vasp_code': 'vasp544mpi',
            'incar_settings': incar_settings,
            'potential_family': potential_family,
            'potential_mapping': potential_mapping,
            }
    relax_settings = deepcopy(base_settings)
    relax_settings.update({
        'kpoints': {'mesh': kpoints['mesh'], 'offset': kpoints['offset']},
        'options': {'queue_name': queue,
                    'max_wallclock_seconds': max_wallclock_seconds},
        'relax_conf': relax_conf,
        'clean_workdir': clean_workdir,
        'parser_settings': parser_settings,
        })
    builder.calculator_settings = Dict(dict={'relax': relax_settings})

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
