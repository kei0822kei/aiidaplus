#!/usr/bin/env python

"""
This script is used when restart vasp job modifying some parameters.
"""

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
    parser.add_argument('--job_pk',
                        type=int,
                        default=None,
                        help="set job_pk")
    args = parser.parse_args()
    return args


args = get_argparse()


@with_dbenv()
def get_elements(pk):
    node = load_node(pk)
    elements = get_elements_from_aiidastructure(node)
    return elements


# ------------------
# job pk for restart
# ------------------
# pk = 255504  # VaspWorkChain
# pk = 255501  # RelaxWorkChain
pk = 256283  # TwinBoundaryRelaxWorkChain


# ---------------
# common settings
# ---------------
label = "this is label"
description = "this is description"



def check_group_existing(group):

    print("------------------------------------------")
    print("check group '%s' exists" % group)
    print("------------------------------------------")
    Group.get(label=group)
    print("OK\n")


def set_relax_conf(builder, relax_conf):
    relax_attribute = AttributeDict()
    keys = relax_conf.keys()
    if 'perform' in keys:
        relax_attribute.perform = \
                Bool(relax_conf['perform'])
    if 'positions' in keys:
        relax_attribute.positions = \
                Bool(relax_conf['positions'])
    if 'volume' in keys:
        relax_attribute.volume = \
                Bool(relax_conf['volume'])
    if 'shape' in keys:
        relax_attribute.shape = \
                Bool(relax_conf['shape'])
    if 'algo' in keys:
        relax_attribute.algo = \
                Str(relax_conf['algo'])
    if 'steps' in keys:
        relax_attribute.steps = \
                Int(relax_conf['steps'])
    if 'convergence_absolute' in keys:
        relax_attribute.convergence_absolute = \
                Bool(relax_conf['convergence_absolute'])
    if 'convergence_max_iterations' in keys:
        relax_attribute.convergence_max_iterations = \
                Int(relax_conf['convergence_max_iterations'])
    if 'convergence_on' in keys:
        relax_attribute.convergence_on = \
                Bool(relax_conf['convergence_on'])
    if 'convergence_positions' in keys:
        relax_attribute.convergence_positions = \
                Float(relax_conf['convergence_positions'])
    if 'convergence_shape_angles' in keys:
        relax_attribute.convergence_shape_angles = \
                Float(relax_conf['convergence_shape_angles'])
    if 'convergence_shape_lengths' in keys:
        relax_attribute.convergence_shape_lengths = \
                Float(relax_conf['convergence_shape_lengths'])
    if 'convergence_volume' in keys:
        relax_attribute.convergence_volume = \
                Float(relax_conf['convergence_volume'])
    if 'force_cutoff' in keys:
        relax_attribute.force_cutoff = \
                Float(relax_conf['force_cutoff'])
    if 'energy_cutoff' in keys:
        relax_attribute.energy_cutoff = \
                Float(relax_conf['energy_cutoff'])
    builder.relax = relax_attribute

@with_dbenv()
def main(computer,
         queue='',
         group=None,
         cmd_label=None,
         cmd_job_pk=None):

    # group check
    if group is not None:
        check_group_existing(group)

    # label
    if cmd_label is None:
        lb = label
    else:
        lb = cmd_label

    # job_pk
    if cmd_job_pk is None:
        job_pk = cmd_job_pk
    else:
        job_pk = pk
    job_node = load_node(job_pk)

    # check job_node is finished
    state = job_node.process_state.value
    print("process state of original job node: {}".format(state))
    if state == 'waiting':
        raise RuntimeError("pk: {} is still running")

    builder = job_node.get_builder_restart()
    builder.metadata.label = lb
    builder.metadata.description = description

    # ========================================================================
    # EDIT HERE
    # ========================================================================
    process_name = builder.process_class.get_name()
    print("process name: {} (pk={})".format(process_name, job_pk))

    # -----
    # relax
    # -----
    if process_name == 'RelaxWorkChain':
        # -- relax_conf
        relax_conf = AiidaRelaxWorkChain(job_node).get_relax_settings()
        relax_conf['positions'] = True
        relax_conf['volume'] = True
        relax_conf['shape'] = True
        relax_conf['force_cutoff'] = 1e-6
        relax_conf['algo'] = 'rd'
        relax_conf['convergence_positions'] = 1e-6
        relax_conf['convergence_volume'] = 1e-5
        set_relax_conf(builder, relax_conf)

        # -- incar
        parameters = job_node.inputs.parameters.get_dict()
        parameters['ediff'] = 1e-8
        builder.parameters = Dict(dict=parameters)

        # -- structure
        builder.structure = job_node.outputs.relax__structure


    # ------------------
    # twinboundary_relax
    # ------------------
    if process_name == 'TwinBoundaryRelaxWorkChain':
        # -- calculator_settings
        calc_settings = job_node.inputs.calculator_settings.get_dict()
        calc_settings['relax']['relax_conf']['positions'] = True
        calc_settings['relax']['relax_conf']['volume'] = True
        calc_settings['relax']['relax_conf']['shape'] = True
        builder.calculator_settings = Dict(dict=calc_settings)


        # -- structure
        # builder.structure = job_node.outputs.final_structure



    # ========================================================================


    # submit
    future = submit(builder)
    print(future)
    print('Running workchain with pk={}'.format(future.pk))
    print('Rebuild from pk={}'.format(job_pk))

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
         cmd_label=args.label,
         cmd_job_pk=args.job_pk)
