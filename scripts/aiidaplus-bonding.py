#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script deals with structure
"""

import argparse
import warnings
import numpy as np
from pprint import pprint
from aiida.cmdline.utils.decorators import with_dbenv
from phonopy.structure.atoms import symbol_map, atom_data
from phonopy.interface.vasp import sort_positions_by_symbols
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.core.structure import Structure
from pymatgen.io.phonopy import get_pmg_structure
from aiidaplus.get_data import get_structure_data_from_pymatgen
from twinpy.interfaces.pymatgen import get_cell_from_pymatgen_structure
from twinpy.structure.bonding import common_neighbor_analysis
import spglib

# argparse
def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--filename', type=str, default=None,
        help="input file name or structure pk")
    parser.add_argument('-t', '--filetype', type=str, default=None,
        help="input file type, currently supported 'cif' or 'poscar' or 'pk'")
    parser.add_argument('--cna', action='store_true',
        help="get common neighbor analysis")
    args = parser.parse_args()
    return args

def get_pmgstructure(filename, filetype, symprec):
    """
    get pymatgen structure object

        Parameters
        ----------
        filename : str
            input file name
        filetype : str
            file type of 'filename'
            currently supported 'cif' or 'poscar'

        Notes
        -----
        occupancy_tolerance = 1.
        - If total occupancy of a site is between 1 and
          occupancy_tolerance, the occupancies will be scaled down to 1.

        site_tolerance = 1e-5
        - This tolerance is used to determine if two sites are sitting
          in the same position, in which case they will be combined to
          a single disordered site.
        - 1e-5 is the same as VASP SYMPREC defualt

        Raises
        ------
        ValueError
            specified filetype is not supported
    """
    occupancy_tolerance = 1.

    if filetype == 'cif':
        from pymatgen.io import cif as pmgcif
        cif = pmgcif.CifParser(filename,
                               occupancy_tolerance=occupancy_tolerance,
                               site_tolerance=symprec)
        pmgstruct = cif.get_structures()[0]
    elif filetype == 'poscar':
        from pymatgen.io.vasp import inputs as pmginputs
        poscar = pmginputs.Poscar.from_file(filename)
        pmgstruct = poscar.structure
    elif filetype == 'pk':
        from aiida.orm import load_node
        node = load_node(int(filename))
        pmgstruct = node.get_pymatgen_structure()
    else:
        raise ValueError("specified filetype is not supported")
    return pmgstruct


@with_dbenv()
def main(filename,
         filetype,
         cna,
         ):

    symprec = 1e-5

    pmgstruct = get_pmgstructure(filename, filetype, symprec)
    cell = get_cell_from_pymatgen_structure(pmgstruct)
    pprint(common_neighbor_analysis(cell))


if __name__ == '__main__':
    args = get_argparse()
    main(filename=args.filename,
         filetype=args.filetype,
         cna=args.cna,
         )
