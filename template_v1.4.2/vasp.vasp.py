#!/usr/bin/env python

import argparse
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.engine import submit
from aiida.orm import (load_node, Bool, Code, Dict, Float,
                       Group, Int, Str, KpointsData)
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
use_relax = True  # if True, use 'vasp.relax' and you have to set relax_conf
wf = 'vasp.relax'
max_wallclock_seconds = 36000
label = "this is label"
description = "this is description"
clean_workdir = True


# ---------
# structure
# ---------
# structure_pk = 30347  # AgBr
# jstructure_pk = 4545  # for glass, Ne
structure_pk = 1252  # for twin,Ti
# structure_pk = 1250  # Ti_c, aiida
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


# ==================
# vasp.vasp settings
# ==================
# -- In the case relax with vasp.vasp workflow
if use_relax == False:
    relax_settings = {
        'nsw': 40,
        'ibrion': 2,
        'isif': 3,
        'ediffg': -1e-4,
        }
    incar_settings.update(relax_settings)


# =====
# encut
# =====
# encut = 300
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


# --------------
# relax_settings
# --------------
# -- If use_relax = True, this conf is used.
if use_relax == True:
    relax_conf = {
        'perform': True,
        'positions': True,
        'volume': True,
        'shape': True,
        'algo': 'rd',  # default: 'cg'
        'steps': 40,
        'convergence_absolute': False,
        'convergence_max_iterations': 2,
        'convergence_on': True,
        'convergence_positions': 0.01,
        'convergence_shape_angles': 0.1,
        'convergence_shape_lengths': 0.1,
        'convergence_volume': 0.01,
        'force_cutoff': 1e-7,  # or 'energy_cutoff': 1e-4,
        }
else:
    relax_conf = None


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
    'mesh': [8, 8, 6],
    'offset': [0, 0, 0.5]
    }


def check_group_existing(group):

    print("------------------------------------------")
    print("check group '%s' exists" % group)
    print("------------------------------------------")
    Group.get(label=group)
    print("OK\n")


def get_builder(dic):

    # set workflow
    if dic['use_relax']:
        wf = 'vasp.relax'
    else:
        wf = 'vasp.vasp'

    # common settings
    workflow = WorkflowFactory(wf)
    builder = workflow.get_builder()
    builder.code = Code.get_from_string(
            '{}@{}'.format('vasp544mpi', dic['computer']))
    builder.clean_workdir = Bool(dic['clean_workdir'])
    builder.verbose = Bool(True)
    builder.metadata.label = dic['metadata']['label']
    builder.metadata.description = dic['metadata']['description']

    # options
    options = AttributeDict()
    options.account = ''
    options.qos = ''
    options.resources = {
            'tot_num_mpiprocs': 16,
            'parallel_env': 'mpi*',
            }
    options.queue_name = dic['options']['queue']
    options.max_wallclock_seconds = dic['options']['max_wallclock_seconds']
    builder.options = Dict(dict=options)

    # structure
    builder.structure = load_node(dic['structure_pk'])

    # incar
    builder.parameters = Dict(dict=dic['incar_settings'])

    # relax
    if dic['use_relax']:
        relax_attribute = AttributeDict()
        keys = relax_conf.keys()
        if 'perform' in keys:
            relax_attribute.perform = \
                    Bool(dic['relax_conf']['perform'])
        if 'positions' in keys:
            relax_attribute.positions = \
                    Bool(dic['relax_conf']['positions'])
        if 'volume' in keys:
            relax_attribute.volume = \
                    Bool(dic['relax_conf']['volume'])
        if 'shape' in keys:
            relax_attribute.shape = \
                    Bool(dic['relax_conf']['shape'])
        if 'algo' in keys:
            relax_attribute.algo = \
                    Str(dic['relax_conf']['algo'])
        if 'steps' in keys:
            relax_attribute.steps = \
                    Int(dic['relax_conf']['steps'])
        if 'convergence_absolute' in keys:
            relax_attribute.convergence_absolute = \
                    Bool(dic['relax_conf']['convergence_absolute'])
        if 'convergence_max_iterations' in keys:
            relax_attribute.convergence_max_iterations = \
                    Int(dic['relax_conf']['convergence_max_iterations'])
        if 'convergence_on' in keys:
            relax_attribute.convergence_on = \
                    Bool(dic['relax_conf']['convergence_on'])
        if 'convergence_positions' in keys:
            relax_attribute.convergence_positions = \
                    Float(dic['relax_conf']['convergence_positions'])
        if 'convergence_shape_angles' in keys:
            relax_attribute.convergence_shape_angles = \
                    Float(dic['relax_conf']['convergence_shape_angles'])
        if 'convergence_shape_lengths' in keys:
            relax_attribute.convergence_shape_lengths = \
                    Float(dic['relax_conf']['convergence_shape_lengths'])
        if 'convergence_volume' in keys:
            relax_attribute.convergence_volume = \
                    Float(dic['relax_conf']['convergence_volume'])
        if 'force_cutoff' in keys:
            relax_attribute.force_cutoff = \
                    Float(dic['relax_conf']['force_cutoff'])
        if 'energy_cutoff' in keys:
            relax_attribute.energy_cutoff = \
                    Float(dic['relax_conf']['energy_cutoff'])
        builder.relax = relax_attribute

    # parser settings
    builder.settings = Dict(dict={'parser_settings': dic['parser_settings']})

    # kpoints
    kpt = KpointsData()
    kpt.set_kpoints_mesh(dic['kpoints']['mesh'],
                         offset=dic['kpoints']['offset'])
    builder.kpoints = kpt

    # potcar
    builder.potential_family = Str(dic['potential_family'])
    builder.potential_mapping = Dict(dict=dic['potential_mapping'])

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
            'use_relax': use_relax,
            'computer': computer,
            'clean_workdir': clean_workdir,
            'metadata': {
                'label': lb,
                'description': description,
                },
            'options': {
                'queue': queue,
                'max_wallclock_seconds': max_wallclock_seconds,
                },
            'structure_pk': structure_pk,
            'incar_settings': incar_settings,
            'relax_conf': relax_conf,
            'parser_settings': parser_settings,
            'kpoints': kpoints,
            'potential_mapping': potential_mapping,
            'potential_family': potential_family,
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
