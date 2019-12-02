#!/usr/bin/env python

import os
import yaml
from aiidaplus import vasp as apvasp
import argparse
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict

# argparse
parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-wf', '--workflow', type=str,
    default='vasp', help="choose workflow, 'vasp'(default), 'relax' or 'phonon'")
parser.add_argument('--code', type=str,
    default=None, help="input code ex. 'vasp544mpi', 'phononpy'")
parser.add_argument('--computer', type=str,
    default=None, help="input computer ex. 'vega'")
parser.add_argument('--kdensity', type=float,
    default=None, help="this arg is used when 'get_setting' is specified \n \
specified kpoints density is INCLUDED 2*pi")
parser.add_argument('--group', type=str,
    default=None, help="add nodes to specified group")
parser.add_argument('--get_settings', type=str,
    default=None, help="get setting file, you don't have to set another parser \n \
input strings are \n \
                        'filetype' 'is_metal' 'filename' \n \
                           filetype: choose from 'oneshot' 'relax' 'phonon'\n \
                           is_metal: bool \n \
                           filename: output filename")
parser.add_argument('--params_yaml', type=str,
    default=None, help="yaml file which contains parameters")
parser.add_argument('--structure_pk', type=int,
    default=None, help="this arg is used when 'get_setting' is specified")
parser.add_argument('--queue', type=str,
    default='', help="queue name, default None")
parser.add_argument('--verbose', action='store_true',
    default=False, help="show detail")
args = parser.parse_args()

def _is_metal(arg_is_metal):
    """
    return bool from input string

        Parameters
        ----------
        arg_is_metal : str
            input string

        Returns
        -------
        is_metal : bool

        Raises
        ------
        ValueError
            arg_is_metal is not 'True' or 'False'
    """
    if parsers[1] == 'True':
        is_metal = True
    elif parsers[1] == 'False':
        is_metal = False
    else:
        raise ValueError("input arg 'is_metal' os not 'True' or 'False'")
    return is_metal

@with_dbenv()
def export_setting(filetype, is_metal, filename, structure_pk, kdensity):
    """
    get aiidaplus-vasp.yaml file

        Parameters
        ----------
        filetype : str
            input file type setting file are exported
            choose from 'oneshot', 'relax' or 'phonopy'
        is_metal : bool
            if structure is metallic, choose True
            otherwise, choose False
        filename : str
            export file name
        structure_pk : int, default None
            if you set 'structure_pk', set stucture
        kdensity : float, default None
            if you set 'kdensity' and 'structure_pk',
            consider the density of kpoints.
            INCLUDED 2 pi

        Returns
        -------
        fruit_price : int
            description

        Notes
        -----

        Raises
        ------
        ValueError
    """
    params = apvasp.default_params(filetype, is_metal, structure_pk, kdensity)
    if os.path.exists(filename):
        print("file %s already exsists, overwrite file" % filename)
    with open(filename, 'w') as f:
        yaml.dump(params, f, indent=4, default_flow_style=False)

@with_dbenv()
def main(code, computer, queue, verbose, wf, params_yaml, group=None):
    from yaml import CLoader as Loader
    from aiida.orm import Code, Group, load_node
    from aiida.plugins import WorkflowFactory
    from aiida.engine import run, submit
    from aiida.common.extendeddicts import AttributeDict
    from aiida_vasp.utils.aiida_utils import get_data_class, get_data_node

    tot_num_mpiprocs = 16

    def _add_node_to_group(running_pk, group):
        # try:
        #     grp = Group.get(label=group)
        # except:
        #     create_grp = Group(label=group)
        #     ctreate_grp.store()
        #     print("group %s did not exist, newly created" % group)
        #     grp = Group.get(label=group)
        grp = Group.get(label=group)
        running_node = load_node(running_pk)
        grp.add_nodes(running_node)
        print("pk {0} is added to group '{1}'".format(running_pk, group))

    def _check_group_existing(group):
        print("------------------------------------------")
        print("check group '%s' exists" % group)
        print("------------------------------------------")
        test_grp = Group.get(label=group)
        print("OK")

    def _unexpected_workflow():
        if wf is not ['vasp', 'relax', 'phonon']:
            raise ValueError("unexpected workflow: %s" % wf)

    def _load_yaml(filename):
        data = yaml.load(open(filename), Loader=Loader)
        return data

    def _get_workflow():
        if wf == 'vasp':
            workflow = WorkflowFactory('vasp.vasp')
        elif wf =='relax':
            workflow = WorkflowFactory('vasp.relax')
        elif wf == 'phonon':
            workflow = WorkflowFactory('phonopy.phonon')
        else:
            _unexpected_workflow()
        return workflow

    def _set_computer_code(builder):
        if code in ['vasp544mpi', 'relax']:
            builder.code = Code.get_from_string('{}@{}'.format(code, computer))
        elif code in ['phonopy']:
            # builder.code_string = Code.get_from_string('{}@{}'.format(code, computer))
            builder.code_string = get_data_node('str', '{}@{}'.format(code, computer))
        else:
            raise ValueError("unexpected code: %s" % wf)

    def _set_clean_workdir(builder):
        if wf in ['vasp', 'relax']:
            builder.clean_workdir = get_data_node('bool', params['clean_workdir'])

    def _set_kpoints(builder):
        """Set a simple kpoint sampling."""
        if code in ['vasp544mpi', 'relax']:
            kpt = get_data_class('array.kpoints')()
            kpt.set_cell_from_structure(builder.structure)
            kpt.set_kpoints_mesh(params['kpoints']['mesh'],
                                 offset=params['kpoints']['offset'])
            builder.kpoints = kpt

    def _set_options(builder):
        options = AttributeDict()
        options.account = ''
        options.qos = ''
        options.resources = {'tot_num_mpiprocs': tot_num_mpiprocs,
                             'parallel_env': 'mpi*'}
        options.queue_name = queue
        options.max_wallclock_seconds = params['options']['max_wallclock_seconds']
        builder.options = get_data_node('dict', dict=options)

    def _set_incar(builder):
        if code in ['vasp544mpi', 'relax']:
            builder.parameters = get_data_node(
                    'dict', dict=params['incar']['incar_base'])
            # if wf == 'relax':
            #     builder.relax_parameters = get_data_node(
            #             'dict', dict=params['incar']['incar_relax'])

    def _set_description(builder):
        builder.metadata.description = params['description']

    def _set_label(builder):
        builder.metadata.label = params['label']

    def _set_potcar(builder):
        if code in ['vasp544mpi', 'relax']:
            builder.potential_family = \
                    get_data_node('str', params['potcar']['potential_family'])
            builder.potential_mapping = \
                    get_data_node('dict', dict=params['potcar']['potential_mapping'])

    def _set_relax_conf(builder):
        if wf == 'relax':
            relax_conf = AttributeDict()
            keys = params['relax_conf'].keys()
            if 'perform' in keys:
                relax_conf.perform = \
                        get_data_node('bool', params['relax_conf']['perform'])
            if 'energy_cutoff' in keys:
                relax_conf.energy_cutoff = \
                        get_data_node('float', params['relax_conf']['energy_cutoff'])
            if 'force_cutoff' in keys:
                relax_conf.force_cutoff = \
                        get_data_node('float', params['relax_conf']['force_cutoff'])
            if 'steps' in keys:
                relax_conf.steps = \
                        get_data_node('int', params['relax_conf']['steps'])
            if 'positions' in keys:
                relax_conf.positions = \
                        get_data_node('bool', params['relax_conf']['positions'])
            if 'shape' in keys:
                relax_conf.shape = \
                        get_data_node('bool', params['relax_conf']['shape'])
            if 'volume' in keys:
                relax_conf.volume = \
                        get_data_node('bool', params['relax_conf']['volume'])
            if 'convergence_on' in keys:
                relax_conf.convergence_on = \
                        get_data_node('bool', params['relax_conf']['convergence_on'])
            if 'convergence_absolute' in keys:
                relax_conf.convergence_absolute = \
                        get_data_node('bool', params['relax_conf']['convergence_absolute'])
            if 'convergence_max_iterations' in keys:
                relax_conf.convergence_max_iterations = \
                        get_data_node('int', params['relax_conf']['convergence_max_iterations'])
            if 'convergence_shape_lengths' in keys:
                relax_conf.convergence_shape_lengths = \
                        get_data_node('float', params['relax_conf']['convergence_shape_lengths'])
            if 'convergence_shape_angles' in keys:
                relax_conf.convergence_shape_angles = \
                        get_data_node('float', params['relax_conf']['convergence_shape_angles'])
            if 'convergence_positions' in keys:
                relax_conf.convergence_positions = \
                        get_data_node('float', params['relax_conf']['convergence_positions'])
            if 'convergence_volume' in keys:
                relax_conf.convergence_volume = \
                        get_data_node('float', params['relax_conf']['convergence_volume'])
            builder.relax = relax_conf

    def _set_phonon(builder):
        def __get_config(is_nac):
            dic = {}
            base_config = {'code_string': 'vasp544mpi@'+computer,
                           'potential_family': params['potcar']['potential_family'],
                           'potential_mapping': params['potcar']['potential_mapping'],
                           'options': {'resources': {'parallel_env': 'mpi*',
                                                     'tot_num_mpiprocs': tot_num_mpiprocs},
                                       'max_wallclock_seconds': 3600 * 10}}
            base_parser_settings = {'add_energies': True,
                                    'add_forces': True,
                                    'add_stress': True}
            forces_config = base_config.copy()
            forces_config.update({'kpoints_mesh': params['kpoints']['mesh_fc2'],  # k-point density,
                                  'parser_settings': base_parser_settings,
                                  'parameters': params['incar']['incar_base']})
            dic['forces'] = forces_config

            if is_nac:
                nac_config = base_config.copy()
                nac_parser_settings = {'add_born_charges': True,
                                       'add_dielectrics': True}
                nac_parser_settings.update(base_parser_settings)
                nac_incar_dict = {'lepsilon': True}
                nac_incar_dict.update(params['incar']['incar_base'])
                nac_config.update({'kpoints_mesh': params['kpoints']['mesh_nac'],
                                   'parser_settings': nac_parser_settings,
                                   'parameters': nac_incar_dict})
                dic['nac'] = nac_config

            return dic

        if wf == 'phonon':
            is_nac = params['phonon_conf']['phonon_settings']['is_nac']
            builder.phonon_settings = get_data_node(
                    'dict', dict=params['phonon_conf']['phonon_settings'])
            builder.run_phonopy = get_data_node('bool', True)
            builder.remote_phonopy = get_data_node('bool', True)
            builder.calculator_settings = get_data_node(
                    'dict', dict=__get_config(is_nac))

    def _set_settings(builder):
        if wf == 'relax':
            builder.settings = get_data_node('dict', dict=
                      {'add_energies': True,
                       'add_forces': True,
                       'add_stress': True}
                    )



    def _set_structure(builder):
        builder.structure = load_node(params['structure_pk'])

    def _set_verbose(builder):
        if wf in ['vasp', 'relax']:
            builder.verbose = get_data_node('bool', verbose)

    ### build
    if group is not None:
        _check_group_existing(group)
    params = _load_yaml(params_yaml)
    workflow = _get_workflow()
    builder = workflow.get_builder()
    _set_structure(builder)
    _set_computer_code(builder)
    _set_options(builder)
    _set_potcar(builder)
    _set_kpoints(builder)
    _set_incar(builder)
    _set_relax_conf(builder)
    _set_verbose(builder)
    _set_clean_workdir(builder)
    _set_description(builder)
    _set_label(builder)
    _set_settings(builder)
    _set_phonon(builder)

    ### run
    # run(workflow, **builder)
    future = submit(workflow, **builder)
    print(future)
    print('Running workchain with pk={}'.format(future.pk))
    if group is not None:
        _add_node_to_group(future.pk, group)


if __name__ == '__main__':
    if args.get_settings is not None:
        parsers = args.get_settings.split()
        export_setting(parsers[0],
                       _is_metal(parsers[1]),
                       parsers[2],
                       args.structure_pk,
                       args.kdensity)
    else:
        main(code=args.code,
             computer=args.computer,
             group=args.group,
             queue=args.queue,
             verbose=args.verbose,
             wf=args.workflow,
             params_yaml=args.params_yaml)
