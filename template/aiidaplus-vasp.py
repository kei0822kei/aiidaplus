#!/usr/bin/env python

### input params
# structure
structure_pk = 1324

# incar
incar_params = {
   'system': 'test system',
   'prec': 'Accurate',
   'encut': 300,
   'ediff': 1e-8,
   'ialgo': 38,
   'ismear': 0,
   'lcharg': False,
   'lwave': False,
   # 'nsw': 20,
   # 'lepsilon': True,
   # 'icharg': 1,
   # 'istart': 1,
   'sigma': 0.1
  }

# kpoints
kpoints_params = {
    'mesh' : [6,6,6],
    'offset' : [0,0,0]
  }

# potcar
# potential_family = 'LDA.54'
potential_family = 'PBE.54'
potential_mapping = {
    'Ga' : 'Ga',
    'As' : 'As'
  }

params = {
    'structure_pk' : structure_pk,
    'incar_params' : incar_params,
    'kpoints_params' : kpoints_params,
    'potential_family' : potential_family,
    'potential_mapping' : potential_mapping
  }

import argparse
from aiida.cmdline.utils.decorators import with_dbenv

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('--code', type=str,
    default=None, help="input code ex. 'vasp544mpi'")
parser.add_argument('--computer', type=str,
    default=None, help="input computer ex. 'vega'")
parser.add_argument('--verbose', action='store_true',
    default=None, help="show detail")
args = parser.parse_args()

@with_dbenv()
def main(code, computer, verbose, params):
    from aiida.orm import Code, load_node
    from aiida.plugins import WorkflowFactory
    from aiida.engine import run
    from aiida.common.extendeddicts import AttributeDict
    from aiida_vasp.utils.aiida_utils import get_data_class, get_data_node

    def _set_kpoints(structure, mesh, offset):
        """Set a simple kpoint sampling."""
        kpoints = get_data_class('array.kpoints')()
        kpoints.set_cell_from_structure(structure)
        kpoints.set_kpoints_mesh(mesh, offset=offset)
        return kpoints

    tot_num_mpiprocs = 16

    # fetch the code to be used (tied to a computer)
    code = Code.get_from_string('{}@{}'.format(code, computer))
    print(str(code))

    # set the WorkChain you would like to call
    # workflow = WorkflowFactory('vasp.vasp')
    workflow = WorkflowFactory('vasp.relax')

    # organize options (needs a bit of special care)
    options = AttributeDict()
    options.account = ''
    options.qos = ''
    options.resources = {'tot_num_mpiprocs': tot_num_mpiprocs,
                         'parallel_env': 'mpi*'}
    options.queue_name = ''
    options.max_wallclock_seconds = 3600

    # the workchains should configure the required parser settings on the fly
    # parser_settings = {'add_forces': True}
    # settings.parser_settings = parser_settings
    # parser_settings = {'add_forces': True,
    #                    'add_stress': True,
    #                    'add_energies': True}
                       # 'add_born_charges': True,
                       # 'add_dielectrics': True,
                       # 'add_chgcar': True,
                       # 'add_wavecar': True,
                       # 'output_params': ['maximum_force']}}

                     # 'ADDITIONAL_RETRIEVE_LIST': ['CHGCAR', 'WAVECAR']}
    # settings = {'parser_settings': parser_settings}

    # set inputs for the following WorkChain execution

    inputs = AttributeDict()
    inputs.code = code
    inputs.structure = load_node(structure_pk)
    inputs.parameters = get_data_node('dict', dict=incar_params)
    inputs.kpoints = _set_kpoints(inputs.structure,
                                 kpoints_params['mesh'],
                                 kpoints_params['offset'])
    inputs.potential_family = get_data_node('str', potential_family)
    inputs.potential_mapping = get_data_node('dict', dict=potential_mapping)
    inputs.options = get_data_node('dict', dict=options)
    # inputs.settings = get_data_node('dict', dict=settings)

    ### vasp.relax setting
    inputs.relax = get_data_node('bool', True)
    inputs.steps = get_data_node('int', 3)
    # inputs.positions = get_data_node('bool', True)
    # inputs.shape = get_data_node('bool', True)
    # inputs.volume = get_data_node('bool', True)
    inputs.convergence_on = get_data_node('bool', True)
    # inputs.convergence_positions = get_data_node('float', 0.1)
    inputs.relax_parameters = get_data_node('dict', dict={
        'ediffg': -0.0001,
        'ibrion': 3,
        'nsw' : 10,
        'isif': 3
    })  # yapf: disable
    inputs.verbose = get_data_node('bool', True)
    run(workflow, **inputs)


if __name__ == '__main__':
    main(code=args.code, computer=args.computer,
         verbose=args.verbose, params=params)
