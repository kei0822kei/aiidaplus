#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script helps you export various data from aiida database.
"""

import argparse
from aiida.orm import load_node
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm.nodes.data.structure import StructureData
from pymatgen.io import vasp as pmgvasp

# argparse
parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-pk', '--node_pk', type=int, default=None,
    help="node pk")
parser.add_argument('--get_data', action='store_true',
    help="get data")
parser.add_argument('--show', action='store_true',
    help="show the detailed information of data")
args = parser.parse_args()

# functions
def _export_structure(pk, pk_data, get_data, show):
    structure = pk_data.get_pymatgen_structure()
    poscar = pmgvasp.Poscar(structure)
    if show:
        print('Object Type: StructureData')
        print('Lattice')
        print(structure.lattice)
        print('Site Symbols')
        print(poscar.site_symbols)
        print('Number of Atoms')
        print(poscar.natoms)
        print('Space Group')
        print(structure.get_space_group_info())

    if get_data:
        poscar.write_file('pk'+str(pk)+'.poscar')


@with_dbenv()
def main(pk, get_data=False, show=False):
    """
    export specified pk data

        Parameters
        ----------
        pk: int
            data node pk
        get_data: bool, default False
            if True, export data
        show: bool, default False
            if True, show detailed information

        Notes
        -----
        object type of specified pk is
          -- StructureData => go to def '_export_structure'
               export structure with POSCAR filetype

        Raises
        ------
        ValueError
            object type of specified pk is not supported
    """
    pk_data = load_node(pk)
    if type(pk_data) is StructureData:
        _export_structure(pk, pk_data, get_data, show)
    else:
        raise ValueError("object type %s is not supported" % type(pk_data))


if __name__ == '__main__':
    main(args.node_pk, args.get_data, args.show)
