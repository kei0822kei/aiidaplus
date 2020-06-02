#!/usr/bin/env python

import os
import yaml
import numpy as np
from aiidaplus import vasp as apvasp
import argparse
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.common.extendeddicts import AttributeDict
from aiida.plugins import DataFactory
from aiida.orm import Float, Bool, Str, Code, Int, Group, load_node
from aiida.engine import run, submit
import yaml


from aiida.plugins import WorkflowFactory

Dict = DataFactory('dict')
ArrayData = DataFactory('array')
StructureData = DataFactory('structure')


# params
structure_pk = 1429
twinmode = '10-12'
twintype = 1
dim = np.array([1,1,2])
# translation = np.array([0.5, 0.5, 0.])
translation_grids = np.array([1, 2, 1])
# dim = [1,1,2]
# translation = [0.5, 0.5, 0.]

@with_dbenv()
def main(structure_pk,
         twinmode,
         twintype,
         dim,
         translation_grids):
    workflow = WorkflowFactory('twinpy.multitwins')
    builder = workflow.get_builder()
    builder.structure = load_node(structure_pk)
    builder.twinmode = Str(twinmode)
    builder.twintype = Int(twintype)
    # builder.dry_run = Bool(True)
    builder.dry_run = Bool(False)
    builder.distance_threshold = Float(0.3)
    dim_array = ArrayData()
    dim_array.set_array('dim', dim)
    builder.dim = dim_array
    translation_grids_array = ArrayData()
    translation_grids_array.set_array('translation_grids', translation_grids)
    builder.translation_grids = translation_grids_array
    with open('Ti_vasp.yaml') as f:
        vasp_settings = yaml.load(f)
    builder.vasp_settings = Dict(dict=vasp_settings)
    # future = run(workflow, **builder)
    submit(workflow, **builder)
    # print('Running workchain with pk={}'.format(future.pk))

if __name__ == '__main__':
    main(structure_pk,
         twinmode,
         twintype,
         dim,
         translation_grids)
