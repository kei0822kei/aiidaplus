#!/usr/bin/env python

import os
import yaml
from aiidaplus import vasp as apvasp
import argparse
from aiida.cmdline.utils.decorators import with_dbenv

# argparse
parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-wf', '--workflow', type=str,
    default='vasp', help="choose workflow, 'vasp'(default) or 'relax'")
parser.add_argument('--code', type=str,
    default=None, help="input code ex. 'vasp544mpi'")
parser.add_argument('--computer', type=str,
    default=None, help="input computer ex. 'vega'")
parser.add_argument('--get_settings', type=str,
    default=None, help="get setting file, you don't have to set another parser \n \
                        input strings are \n \
                        'filetype' 'is_metal' 'filename' \n \
                          filetype: choose from 'oneshot' 'relax' \n \
                          is_metal: bool \n \
                          filename: output filename")
parser.add_argument('--params_yaml', type=str,
    default=None, help="yaml file which contains parameters")
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

def export_setting(filetype, is_metal, filename):
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
    params = apvasp.default_params(filetype, is_metal)
    if os.path.exists(filename):
        print("file %s already exsists, overwrite file" % filename)
    with open(filename, 'w') as f:
        yaml.dump(params, f, indent=4, default_flow_style=False)

@with_dbenv()
def main(code, computer, queue, verbose, wf, params_yaml):
    from yaml import CLoader as Loader
    from aiida.orm import Code, load_node
    from aiida.plugins import WorkflowFactory
    from aiida.engine import run
    from aiida.common.extendeddicts import AttributeDict
    from aiida_vasp.utils.aiida_utils import get_data_class, get_data_node

    def _load_yaml(filename):
        data = yaml.load(open(filename), Loader=Loader)
        return data

    def _get_workflow(wf):
        if wf == 'vasp':
            workflow = WorkflowFactory('vasp.vasp')
        elif wf =='relax':
            workflow = WorkflowFactory('vasp.relax')
        else:
            raise ValueError("unexpected workflow: %s" % wf)
        return workflow

    def _set_computer_code(builder, code, computer):
        builder.code = Code.get_from_string('{}@{}'.format(code, computer))

    def _set_clean_workdir(builder, clean_workdir):
        builder.clean_workdir = get_data_node('bool', clean_workdir)

    def _set_kpoints(builder, kpoints):
        """Set a simple kpoint sampling."""
        kpt = get_data_class('array.kpoints')()
        kpt.set_cell_from_structure(builder.structure)
        kpt.set_kpoints_mesh(kpoints['mesh'], offset=kpoints['offset'])
        builder.kpoints = kpt

    def _set_options(builder):
        tot_num_mpiprocs = 16
        options = AttributeDict()
        options.account = ''
        options.qos = ''
        options.resources = {'tot_num_mpiprocs': tot_num_mpiprocs,
                             'parallel_env': 'mpi*'}
        options.queue_name = queue
        options.max_wallclock_seconds = 3600
        builder.options = get_data_node('dict', dict=options)

    def _set_incar(builder, wf, incar):
        builder.parameters = get_data_node('dict', dict=incar['incar_base'])
        if wf == 'relax':
            builder.relax_parameters = get_data_node('dict', dict=incar['incar_relax'])

    def _set_potcar(builder, potcar):
        builder.potential_family = \
                get_data_node('str', potcar['potential_family'])
        builder.potential_mapping = \
                get_data_node('dict', dict=potcar['potential_mapping'])

    def _set_relax_conf(builder, relax_conf):
        builder.relax = \
                get_data_node('bool', relax_conf['relax'])
        # builder.steps = \
        #         get_data_node('int', relax_conf['steps'])
        # builder.positions = \
        #         get_data_node('bool', relax_conf['positions'])
        # builder.shape = \
        #         get_data_node('bool', relax_conf['shape'])
        # builder.volume = \
        #         get_data_node('bool', relax_conf['volume'])
        builder.convergence_on = \
                get_data_node('bool', relax_conf['convergence_on'])
        builder.convergence_absolute = \
                get_data_node('bool', relax_conf['convergence_absolute'])
        builder.convergence_max_iterations = \
                get_data_node('int', relax_conf['convergence_max_iterations'])
        builder.convergence_shape_lengths = \
                get_data_node('float', relax_conf['convergence_shape_lengths'])
        builder.convergence_shape_angles = \
                get_data_node('float', relax_conf['convergence_shape_angles'])
        builder.convergence_positions = \
                get_data_node('float', relax_conf['convergence_positions'])
        builder.convergence_volume = \
                get_data_node('float', relax_conf['convergence_volume'])

    def _set_structure(builder, structure_pk):
        builder.structure = load_node(structure_pk)

    def _set_verbose(builder):
        builder.verbose = get_data_node('bool', verbose)

    ### build
    params = _load_yaml(params_yaml)
    workflow = _get_workflow(wf)
    builder = workflow.get_builder()
    _set_structure(builder, params['structure_pk'])
    _set_computer_code(builder, code, computer)
    _set_options(builder)
    _set_potcar(builder, params['potcar'])
    _set_kpoints(builder, params['kpoints'])
    _set_incar(builder, wf, params['incar'])
    if wf == 'relax':
        _set_relax_conf(builder, params['relax_conf'])
    _set_verbose(builder)
    _set_clean_workdir(builder, params['clean_workdir'])

    ### run
    run(workflow, **builder)


if __name__ == '__main__':
    if args.get_settings is not None:
        parsers = args.get_settings.split()
        export_setting(parsers[0], _is_metal(parsers[1]), parsers[2])
    else:
        main(code=args.code, computer=args.computer, queue=args.queue,
             verbose=args.verbose, wf=args.workflow, params_yaml=args.params_yaml)
