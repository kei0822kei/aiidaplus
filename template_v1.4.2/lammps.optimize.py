#!/usr/bin/env python

import argparse
import numpy as np
from aiida.common.extendeddicts import AttributeDict
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm import load_node, Code, Dict, Group, StructureData
from aiida.plugins import CalculationFactory
from aiida.engine import submit
from aiida_lammps.data.potential import EmpiricalPotential


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


# ---------------
# common settings
# ---------------
max_wallclock_seconds = 36000
label = "this is label"
description = "this is description"


# ---------
# calc type
# ---------
# calc = 'lammps.optimize'
calc = 'lammps.force'

use_dynaphopy = False

### currently cannot use
### If you want to use,
### use aiida-phonopy before (2020/11/14) or fix original code.
# use_dynaphopy = True


# ---------
# structure
# ---------
# structure_pk = 51030  # glass. GaN primitive
structure_pk = 52121  # glass. Si conventional


# ---------
# potential
# ---------

pair_style = 'tersoff'

# GaN
# tersoff = {
#     'Ga Ga Ga': '1.0 0.007874 1.846 1.918000 0.75000 -0.301300 1.0 1.0 1.44970 410.132 2.87 0.15 1.60916 535.199',
#     'N  N  N': '1.0 0.766120 0.000 0.178493 0.20172 -0.045238 1.0 1.0 2.38426 423.769 2.20 0.20 3.55779 1044.77',
#     'Ga Ga N': '1.0 0.001632 0.000 65.20700 2.82100 -0.518000 1.0 0.0 0.00000 0.00000 2.90 0.20 0.00000 0.00000',
#     'Ga N  N': '1.0 0.001632 0.000 65.20700 2.82100 -0.518000 1.0 1.0 2.63906 3864.27 2.90 0.20 2.93516 6136.44',
#     'N  Ga Ga': '1.0 0.001632 0.000 65.20700 2.82100 -0.518000 1.0 1.0 2.63906 3864.27 2.90 0.20 2.93516 6136.44',
#     'N  Ga N ': '1.0 0.766120 0.000 0.178493 0.20172 -0.045238 1.0 0.0 0.00000 0.00000 2.20 0.20 0.00000 0.00000',
#     'N  N  Ga': '1.0 0.001632 0.000 65.20700 2.82100 -0.518000 1.0 0.0 0.00000 0.00000 2.90 0.20 0.00000 0.00000',
#     'Ga N  Ga': '1.0 0.007874 1.846 1.918000 0.75000 -0.301300 1.0 0.0 0.00000 0.00000 2.87 0.15 0.00000 0.00000',
# }

# Si
tersoff = {
    'Si  Si  Si ': '3.0 1.0 1.7322 1.0039e5 16.218 -0.59826 0.78734 1.0999e-6  1.7322  471.18  2.85  0.15  2.4799  1830.8'
        }

data = tersoff


# ----------
# parameters
# ----------
if use_dynaphopy:

    if calc == 'lammps.optimize':
        dynaphopy_settings = None

    elif calc == 'lammps.force':
        # force_constants_pk = 52127  # glass. Si tersoff force constants
        # parameters = {
        #     "timestep": 0.001,
        #     "temperature": 300,
        #     "thermostat_variable": 0.5,
        #     "equilibrium_steps": 2000,
        #     "total_steps": 2000,
        #     "dump_rate": 1,
        # }
        # parameters = None
        # dynaphopy_parameters = {
        #     "supercell": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
        #     "primitive": [[0.0, 0.5, 0.5], [0.5, 0.0, 0.5], [0.5, 0.5, 0.0]],
        #     "mesh": [40, 40, 40],
        #     "md_commensurate": False,
        #     "md_supercell": [2, 2, 2],
        # }
        # dynaphopy_settings = {
        #     'parameters': dynaphopy_parameters,
        #     'force_constants_pk': force_constants_pk,
        #     }

else:

    if calc == 'lammps.optimize':
        parameters = {
            'units': 'metal',
            'relax': {
                'type': 'tri',  # iso/aniso/tri
                'pressure': 0.0,  # bars
                'vmax': 0.000001,  # Angstrom^3
            },
            'minimize': {
                'style': 'cg',
                'energy_tolerance': 1.0e-25,  # eV
                'force_tolerance': 1.0e-25,  # eV angstrom
                'max_evaluations': 1000000,
                'max_iterations': 500000,
            },
        }
        dynaphopy_settings = None

    elif calc == 'lammps.force':
        parameters = None
        dynaphopy_settings = None


# ---------
# dynaphopy
# ---------


def check_group_existing(group):

    print("------------------------------------------")
    print("check group '%s' exists" % group)
    print("------------------------------------------")
    Group.get(label=group)
    print("OK\n")


def get_tot_num_mpiprocs(computer, queue):

    tot_num = 16
    if computer == 'vega':
        if queue == 'vega-b':
            tot_num = 32
        elif queue == 'vega-c':
            tot_num = 80

    return tot_num


def get_builder(dic):

    calcfunc = CalculationFactory(dic['calc'])
    builder = calcfunc.get_builder()
    builder.code = Code.get_from_string(
            '{}@{}'.format('lammps', dic['computer']))
    builder.metadata.label = dic['metadata']['label']
    builder.metadata.description = dic['metadata']['description']

    # options
    options = AttributeDict()
    options.account = ''
    options.qos = ''
    options.resources = {
            'tot_num_mpiprocs': dic['metadata']['options']['tot_num_mpiprocs'],
            'parallel_env': 'mpi*',
            }
    options.queue_name = dic['metadata']['options']['queue']
    options.max_wallclock_seconds = \
            dic['metadata']['options']['max_wallclock_seconds']
    builder.metadata.options = options

    # structure
    builder.structure = load_node(dic['structure_pk'])

    # potential
    builder.potential = EmpiricalPotential(
            type=dic['potential']['pair_style'],
            data=dic['potential']['data'])

    # parameters
    if dic['calc'] == 'lammps.optimize':
        if use_dynaphopy:
            pass
        else:
            builder.parameters = Dict(dict=dic['parameters'])
    elif dic['calc'] == 'lammps.force':
        if use_dynaphopy:
            builder.parameters = Dict(dict=dic['parameters'])
            builder.parameters_dynaphopy = \
                    Dict(dict=dic['dynaphopy_settings']['parameters'])
            builder.force_constants(
                    load_node(dic['dynaphopy_settings']['force_constants_pk']))
        else:
            pass

    return builder


@with_dbenv()
def main(computer,
         queue='',
         group=None,
         cmd_label=None):

    # group check
    if group is not None:
        check_group_existing(group)

    # label
    if cmd_label is None:
        lb = label
    else:
        lb = cmd_label

    # tot_num_mpiprocs
    tot_num_mpiprocs = get_tot_num_mpiprocs(computer, queue)

    dic = {
            'calc': calc,
            'use_dynaphopy': use_dynaphopy,
            'computer': computer,
            'metadata': {
                'label': lb,
                'description': description,
                'options': {
                    'queue': queue,
                    'max_wallclock_seconds': max_wallclock_seconds,
                    'tot_num_mpiprocs': tot_num_mpiprocs,
                    },
                },
            'structure_pk': structure_pk,
            'potential': {
                'pair_style': pair_style,
                'data': data,
                },
            'parameters': parameters,
            'dynaphopy_settings': dynaphopy_settings,
          }

    builder = get_builder(dic=dic)

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
