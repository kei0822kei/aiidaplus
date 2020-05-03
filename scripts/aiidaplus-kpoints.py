#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script deals with structure
"""

import argparse
import numpy as np
from pprint import pprint
from aiida.cmdline.utils.decorators import with_dbenv
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from aiidaplus.get_data import get_structure_data_from_pymatgen
from aiidaplus.utils import get_kpoints

# argparse
def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--filename', type=str, default=None,
        help="input file name or structure pk")
    parser.add_argument('-t', '--filetype', type=str, default=None,
        help="input file type, currently supported 'cif' or 'poscar' or 'pk'")
    parser.add_argument('--kdensity', type=float, default=None,
        help="kdensity")
    parser.add_argument('--mesh', type=str, default=None,
        help="mesh ex. '6 6 6'")
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
         kdensity,
         mesh):

    symprec = 1e-5

    pmgstruct = get_pmgstructure(filename, filetype, symprec)
    kpts = get_kpoints(pmgstruct, mesh=mesh, kdensity=kdensity, verbose=True)

if __name__ == '__main__':
    args = get_argparse()
    if args.kdensity is None and args.mesh is None:
        raise ValueError("both mesh and kdensity are not specified")
    if args.kdensity is not None and args.mesh is not None:
        raise ValueError("both mesh and kdensity are specified")

    if args.mesh is not None:
        mesh = np.array(list(map(int, args.mesh.split())))
    else:
        mesh = None
    main(filename=args.filename,
         filetype=args.filetype,
         kdensity=args.kdensity,
         mesh=mesh)
