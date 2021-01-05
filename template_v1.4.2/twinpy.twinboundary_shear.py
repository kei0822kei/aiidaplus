#!/usr/bin/env python

import argparse
from aiida import load_profile
from aiida.plugins import WorkflowFactory
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.engine import submit
from aiida.orm import (load_node, Dict,
                       Group, Str)

load_profile()


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


# ---------------------
# twinpy shear settings
# ---------------------
twinboundary_shear_conf = {
    'twinboundary_relax_pk': 483622,
    'additional_relax_pks': [539358],
    'shear_strain_ratios': [0.01, 0.02, 0.03],
    }

# kpoints_interval = 0.15
# kpoints_interval = None

# ---------------
# common settings
# ---------------
wf = 'twinpy.twinboundary_shear'
label = "twinpy twinboundary relax calc {} using relax result (pk: {})".format(
        twinboundary_shear_conf['twinboundary_relax_pk'],
        twinboundary_shear_conf['additional_relax_pks'][-1])
description = label


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

    twinboundary_shear_conf['options'] = {
            'queue_name': queue,
            'max_wallclock_seconds': 100 * 3600,
            }
    builder.twinboundary_shear_conf = Dict(dict=twinboundary_shear_conf)
    # if kpoints_interval is not None:
    #     builder.kpoints_interval = kpoints_interval

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
