#!/usr/bin/env python

import argparse
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import submit
from aiida.orm import (load_node, Bool, Dict, Group, Str)
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
tot_num_mpiprocs = 16
max_wallclock_seconds = 1000 * 3600
label = "this is label"
description = "this is description"


# ---------
# structure
# ---------
# structure_pk = 4775  # Ti
# structure_pk = 30401  # AgBr (relaxed)
# structure_pk = 4545  # Ne, for glass database
# structure_pk = 11850  # Ti, glass database
structure_pk = 6836  # Ti, relaxed, aiida database
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
    'kpar': 2,
    'prec': 'Accurate',
    }


# =====
# encut
# =====
# encut = 375
encut = int(get_encut(potential_family=potential_family,
                      potential_mapping=potential_mapping,
                      multiply=1.3))

incar_settings['encut'] = encut

# =====
# smear
# =====
# -- metal
smearing_settings = {
    'ismear': 1,
    'sigma': 0.4
    }

# -- not metal
# smearing_settings = {
#     'ismear': 0,
#     'sigma': 0.01
#     }

incar_settings.update(smearing_settings)


# -----------------------
# kpoints for fc2 and nac
# -----------------------
kpoints_fc2 = {
    'mesh': [3, 3, 3],
    'offset': [0.5, 0.5, 0.5]
    }

# when calculating nac phonopy always uses primitive
# 'offset' is set by phonopy automatically ?
kpoints_nac = {
    'mesh': [12, 12 ,12],
    # 'offset': [0,0,0],  # there is no input parameters, see script below
    }


# -------
# phonopy
# -------
# vasp_code = 'vasp544mpi'
tot_num_mpiprocs = 16
distance = 0.03
is_nac = False
# is_nac = True
phonopy_mesh = [13,13,13]
supercell_matrix = [2,2,2]
symmetry_tolerance = 1e-5


def check_group_existing(group):
    print("------------------------------------------")
    print("check group '%s' exists" % group)
    print("------------------------------------------")
    Group.get(label=group)
    print("OK\n")


def get_builder(dic):

    def _get_vasp_settings(computer, options, is_nac, calc):

        vasp_settings = {}

        # base settings
        base_config = {
            'code_string': 'vasp544mpi'+'@'+computer,
            'kpoints_mesh': calc['kpoints_fc2']['mesh'],
            'kpoints_offset': calc['kpoints_fc2']['offset'],
            'potential_family': calc['potential_family'],
            'potential_mapping': calc['potential_mapping'],
            'options': {'resources': {'parallel_env': 'mpi*',
                                      'tot_num_mpiprocs':
                                              calc['tot_num_mpiprocs']},
                        'queue_name': options['queue'],
                        'max_wallclock_seconds':
                                options['max_wallclock_seconds'],
                        },
            }
        base_parser_settings = {'add_energies': True,
                                'add_forces': True,
                                'add_stress': True}

        # forces settings
        forces_config = base_config.copy()
        forces_config.update({'parser_settings': base_parser_settings,
                              'parameters': calc['incar_settings']})
        vasp_settings['forces'] = forces_config

        if is_nac:
            nac_config = base_config.copy()
            nac_parser_settings = {'add_born_charges': True,
                                   'add_dielectrics': True}
            nac_parser_settings.update(base_parser_settings)
            nac_incar_dict = {'lepsilon': True}
            nac_incar_dict.update(calc['incar_settings'])
            del nac_incar_dict['npar']
            del nac_incar_dict['kpar']
            nac_config.update({'kpoints_mesh': calc['nac_mesh'],
                               'parser_settings': nac_parser_settings,
                               'parameters': nac_incar_dict})
            vasp_settings = nac_config

        return vasp_settings

    # common settings
    wf = 'phonopy.phonopy'
    code = 'phonopy'
    workflow = WorkflowFactory(wf)
    builder = workflow.get_builder()
    builder.code_string = Str(
            '{}@{}'.format(code, dic['computer']))
    builder.metadata.label = dic['metadata']['label']
    builder.metadata.description = dic['metadata']['description']

    # options
    options = AttributeDict()
    options.account = ''
    options.qos = ''
    # -- does it work when global tot_num_mpiprocs=32 ?
    options.resources = {'parallel_env': 'mpi*',
                         'tot_num_mpiprocs': 16}
    options.queue_name = dic['options']['queue']
    options.max_wallclock_seconds = dic['options']['max_wallclock_seconds']
    builder.options = Dict(dict=options)

    # structure
    builder.structure = load_node(dic['structure_pk'])

    # phonopy
    builder.phonon_settings = Dict(dict=dic['phonon_settings'])
    builder.run_phonopy = Bool(True)
    builder.remote_phonopy = Bool(True)
    builder.calculator_settings = \
            Dict(dict=_get_vasp_settings(
                          computer=dic['computer'],
                          options=dic['options'],
                          is_nac=dic['phonon_settings']['is_nac'],
                          calc=dic['calculator_settings'],
                          )
                 )

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

    # get builder
    dic = {
            'computer': computer,
            'metadata': {
                'label': lb,
                'description': description,
                },
            'options': {
                'queue': queue,
                'max_wallclock_seconds': max_wallclock_seconds,
                },
            'structure_pk': structure_pk,
            'phonon_settings': {
                'distance': distance,
                'is_nac': is_nac,
                'mesh': phonopy_mesh,
                'supercell_matrix': supercell_matrix,
                'symmetry_tolerance': symmetry_tolerance,
                },
            'calculator_settings': {
                'kpoints_fc2': kpoints_fc2,
                'potential_family': potential_family,
                'potential_mapping': potential_mapping,
                'tot_num_mpiprocs': tot_num_mpiprocs,
                'incar_settings': incar_settings,
                'nac_mesh': kpoints_nac['mesh'],
                },
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
