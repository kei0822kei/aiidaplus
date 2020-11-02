#!/usr/bin/env python

import argparse
from copy import deepcopy
from aiida.plugins import WorkflowFactory
from aiida.engine import submit
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm import load_node, Bool, Dict, Group, Str, Float
from aiidaplus.utils import (get_default_potcar_mapping,
                             get_encut)
from twinpy.interfaces.aiida import AiidaRelaxWorkChain


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
def get_AiidaRelaxWorkChain(relax_pk):
    relax = AiidaRelaxWorkChain(node=load_node(relax_pk))
    return relax


# ======= EDIT HERE ================================

relax_pk = 7887  # relax  Mg_pv
label = "this is label"
description = "this is description"

shear_conf = {
        'twinmode': '10-12',
        'grids': 5,
        }

supercell_matrix = [2, 2, 2]
mesh_phonon = [9, 9, 6]
use_kpoints_interval = True
kpoints_interval = 0.15

# ======= EDIT HERE ================================


# -----------------------
# get AiidaRelaxWorkChain
# -----------------------
relax = get_AiidaRelaxWorkChain(relax_pk=relax_pk)
inputs = relax.get_vasp_settings()


# ---------------
# common settings
# ---------------
wf = 'twinpy.shear'
dry_run = False
# dry_run = True
is_phonon = True
max_wallclock_seconds_relax = 100 * 3600
max_wallclock_seconds_phonon = 1000 * 3600
clean_workdir = True
vasp_code = 'vasp544mpi'


# -----------
# phonon_conf
# -----------
phonon_conf = {
    'distance': 0.03,
    'mesh': [18, 18, 10],
    'supercell_matrix': supercell_matrix,
    'symmetry_tolerance': 1e-5
    }

# -------
# kpoints
# -------
kpoints = {
    'mesh': inputs['kpoints'][0],
    'offset': inputs['kpoints'][1],
    }

kpoints_phonon = {
    'mesh': mesh_phonon,
    'offset': inputs['kpoints'][1],
    }


# ---------
# structure
# ---------
structure_pk = relax.get_pks()['final_structure_pk']


# ------
# potcar
# ------
potential_family = inputs['potcar']['potential_family']
potential_mapping = inputs['potcar']['potential_mapping']


# -----
# incar
# -----
incar_settings = inputs['incar']


# --------------
# relax_settings
# --------------
relax_conf = relax.get_relax_settings()
relax_conf['perform'] = True
relax_conf['positions'] = True
relax_conf['volume'] = False
relax_conf['shape'] = False
parser_settings = inputs['parser_settings']


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

    # kpoints setting
    builder.use_kpoints_interval = Bool(use_kpoints_interval)
    if use_kpoints_interval:
        builder.kpoints_interval = Float(kpoints_interval)

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
