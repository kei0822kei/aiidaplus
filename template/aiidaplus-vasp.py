#!/usr/bin/env python

### input params
# structure
structure_pk = 1324

# incar
static_params = {
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

relax_params = {
    'ediffg': -0.0001,
    'ibrion': 3,
    # 'nsw' : 10,
    # 'isif': 3
  }

"""
# relax_conf parameters

### relax
  type: Bool, default: False
  (do not perform relaxations)

### steps
  type: Int, default: 60
  (the number of ionic positions updates to perform)

### positions
  type: Bool, default: True
  (if relax is True, perform relaxations of the atomic positions)

### shape
  type: Bool, default: False
  (if relax is True, perform relaxation of the cell shape)

### volume
  type: Bool, default: False
  (if relax is True, perform relaxation of the cell volume)

### convergence_on
  type: Bool, default: False
  (do not check or run additional relaxations)

### convergence_absolute
  type: Bool, default: False
  (with respect to the previous relaxation)
    - False: relative tolerances are used (relative convergence)
    - True: absolute tolerances are used (native VASP units)

### convergence_max_iterations
  type: Int, default: 5
  (execute a maximum of five relaxation runs)

### convergence_shape_lengths
  type: Float, default: 0.1
  (allow a maximum of 10 % change of the L2 norm for the unitcell vectors
   from the previous relaxation)

### convergence_shape_angles
  type: Float, default: 0.1
  (allow a maximum of 10 % change of the unitcell angles
   from the previous relaxation)

### convergence_volume
  type: Float, default: 0.01
  (allow a maximum of 1 % change of the unitcell volume
   from the previous relaxation)

### convergence_positions
  type: Float, default: 0.01
  (allow a maximum of 1 % displacement (L2 norm) of the positions
   from the previous relaxation)
"""

relax_conf = {
    'relax': True,
    'steps': 60,
    'positions': True,
    'shape': True,
    'volume': True,
    'convergence_on': True,
    'convergence_absolute': False,
    'convergence_max_iterations': 5,
    'convergence_shape_lengths': 0.1,
    'convergence_shape_angles': 0.1,
    'convergence_volume': 0.01,
    'convergence_positions': 0.01
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

import argparse
from aiida.cmdline.utils.decorators import with_dbenv

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-wf', '--workflow', type=str,
    default='vasp', help="choose workflow, 'vasp'(default) or 'relax'")
parser.add_argument('--code', type=str,
    default=None, help="input code ex. 'vasp544mpi'")
parser.add_argument('--computer', type=str,
    default=None, help="input computer ex. 'vega'")
parser.add_argument('--queue', type=str,
    default=None, help="queue name, default None")
parser.add_argument('--verbose', action='store_true',
    default=False, help="show detail")
args = parser.parse_args()

@with_dbenv()
def main(code, computer, queue, verbose, wf):
    from aiida.orm import Code, load_node
    from aiida.plugins import WorkflowFactory
    from aiida.engine import run
    from aiida.common.extendeddicts import AttributeDict
    from aiida_vasp.utils.aiida_utils import get_data_class, get_data_node

    tot_num_mpiprocs = 16

    def _set_kpoints(structure, mesh, offset):
        """Set a simple kpoint sampling."""
        kpoints = get_data_class('array.kpoints')()
        kpoints.set_cell_from_structure(structure)
        kpoints.set_kpoints_mesh(mesh, offset=offset)
        return kpoints

    ### fetch the code to be used (tied to a computer)
    comp_code = Code.get_from_string('{}@{}'.format(code, computer))
    print('code: %s' % str(comp_code))

    ### set the WorkChain you would like to call
    if wf == 'vasp':
        workflow = WorkflowFactory('vasp.vasp')
    elif wf =='relax':
        workflow = WorkflowFactory('vasp.relax')
    else:
        raise ValueError("unexpected workflow: %s" % wf)
    # workflow.label = 'hogehoge'
    # workflow.description = 'hogehoge hogehoge'

    ### organize options (needs a bit of special care)
    options = AttributeDict()
    options.account = ''
    options.qos = ''
    options.resources = {'tot_num_mpiprocs': tot_num_mpiprocs,
                         'parallel_env': 'mpi*'}
    options.queue_name = queue
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

    ### set inputs for the following WorkChain execution
    inputs = AttributeDict()
    inputs.code = comp_code
    inputs.structure = load_node(structure_pk)
    inputs.parameters = get_data_node('dict', dict=static_params)
    inputs.kpoints = _set_kpoints(inputs.structure,
                                  kpoints_params['mesh'],
                                  kpoints_params['offset'])
    inputs.potential_family = get_data_node('str', potential_family)
    inputs.potential_mapping = get_data_node('dict', dict=potential_mapping)
    inputs.options = get_data_node('dict', dict=options)
    inputs.verbose = get_data_node('bool', verbose)
    # inputs.settings = get_data_node('dict', dict=settings)

    ### vasp.relax setting
    if wf == 'relax':
        inputs.relax = \
                get_data_node('bool', relax_conf['relax'])
        inputs.positions = \
                get_data_node('bool', relax_conf['positions'])
        inputs.shape = \
                get_data_node('bool', relax_conf['shape'])
        inputs.volume = \
                get_data_node('bool', relax_conf['volume'])
        inputs.convergence_on = \
                get_data_node('bool', relax_conf['convergence_on'])
        inputs.convergence_absolute = \
                get_data_node('bool', relax_conf['convergence_absolute'])
        inputs.convergence_max_iterations = \
                get_data_node('int', relax_conf['convergence_max_iterations'])
        inputs.convergence_shape_lengths = \
                get_data_node('float', relax_conf['convergence_shape_lengths'])
        inputs.convergence_shape_angles = \
                get_data_node('float', relax_conf['convergence_shape_angles'])
        inputs.convergence_positions = \
                get_data_node('float', relax_conf['convergence_positions'])
        inputs.convergence_volume = \
                get_data_node('float', relax_conf['convergence_volume'])
        inputs.relax_parmas = get_data_node('dict', relax_params)

    ### run
    run(workflow, **inputs)


if __name__ == '__main__':
    main(code=args.code, computer=args.computer, queue=args.queue,
         verbose=args.verbose, wf=args.workflow)
