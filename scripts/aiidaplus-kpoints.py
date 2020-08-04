#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script deals with structure
"""

import argparse
import numpy as np
from pprint import pprint
from aiida.cmdline.utils.decorators import with_dbenv
from twinpy.common.kpoints import get_mesh_offset_from_direct_lattice


# argparse
def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--filename',
                        type=str,
                        default=None,
                        help="input file name or structure pk")
    parser.add_argument('-t', '--filetype',
                        type=str,
                        default=None,
                        help="input file type, currently supported "
                             "'cif' or 'poscar' or 'pk'")
    parser.add_argument('--interval',
                        type=float,
                        default=None,
                        help="interval")
    parser.add_argument('--mesh',
                        type=str,
                        default=None,
                        help="mesh ex. '6 6 6'")
    args = parser.parse_args()
    return args


def get_pmgstructure(filename, filetype, symprec):
    """
    Get pymatgen structure object.
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
         interval,
         mesh):

    symprec = 1e-5

    pmgstruct = get_pmgstructure(filename, filetype, symprec)
    lattice = pmgstruct.lattice.matrix
    kpts = get_mesh_offset_from_direct_lattice(
            lattice=lattice,
            interval=interval,
            mesh=mesh,
            include_two_pi=True
            )
    print(pmgstruct)
    print("\n\n")
    print("# ----------------------")
    print("# Reciprocal Information")
    print("# ----------------------")
    for key in kpts.keys():
        print("%s:" % key)
        pprint(kpts[key])
        print("")


if __name__ == '__main__':
    args = get_argparse()
    if args.mesh is not None:
        mesh = np.array(list(map(int, args.mesh.split())))
    else:
        mesh = None
    main(filename=args.filename,
         filetype=args.filetype,
         interval=args.interval,
         mesh=mesh)
