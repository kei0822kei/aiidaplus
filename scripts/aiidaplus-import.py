#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script helps you import various data to aiida database.
"""

import argparse
from aiida.cmdline.utils.decorators import with_dbenv

# argparse
parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-f', '--filename', type=str, default=None,
    help="input file name \n\n")
parser.add_argument('-k', '--kpoints', type=str, default=None,
    help="import kpoints from command line \n"
         "if you use this option, it's not necessary to specify the other options"
         "ex. '6,6,6 0.5,0.5,0 m' \n\n")
parser.add_argument('-t', '--filetype', type=str, default=None,
    help="input file type, currently supported 'cif' or 'poscar' \n\n")
parser.add_argument('-c', '--comment', type=str, default=None,
    help="comment which is included with imported data \n\n")
args = parser.parse_args()


# functions
def _detect_run_mode(filetype):
    """
    decide run mode

        Parameters
        ----------
        filetype : str

        Returns
        -------
        data_type : str
            return import data type

        Raises
        ------
        ValueError
            unexpected filetype
    """
    if filetype in ['cif', 'poscar']:
        data_type = 'structure'
    elif filetype == 'kpoints':
        data_type = 'kpoints'
    else:
        raise ValueError("specified filetype is not supported")

    return data_type
# 
# 
def import_Kpoints(filename=None, kpoints_string=None):
    """
    import kpoints data

        Parameters
        ----------
        filename : str, default None
            KPOINTS file
        kpoints_string : str, default None
            input kpoints string

        Notes
        -----
        you can input 'filename' or 'kpoints_string'
        do not input both

        Raises
        ------
        ValueError
            both 'filename' and 'kpoints_string' are input
            both 'filename' and 'kpoints_string' are None
    """
    def _shape_input_string(kpoints_string):
        """
        shape input string for kpoints

            Raise
            -----
            ValueError
                "length <input string> is not 3"
                "unexpected kpoints style specified"

            Returns
            -------
            kpoints : dict
                ex.
                dict {'mesh'  : [6,6,6],
                      'shift' : [0,0.5,0],
                      'style' : 'Monkhorst-pack'}
        """
        lst = kpoints_string.split()
        if len(lst) != 3:
            raise ValueError("length <input string> is not 3")

        kpoints ={}
        kpoints['mesh'] = list(map(int, lst[0].replace(',',' ').split()))
        kpoints['shift'] = list(map(float, lst[1].replace(',',' ').split()))
        if lst[2] == 'm':
            kpoints['style'] = 'Monkhorst'
        else:
            raise ValueError("unexpected kpoints style specified")
        return kpoints

    def _shape_kpoints_file(filename):
        """
        shape kpoints file

            Returns
            -------
            kpoints : dict
                ex.
                dict {'mesh'  : [6,6,6],
                      'shift' : [0,0.5,0],
                      'style' : 'Monkhorst'}
        """
        from pymatgen.io import vasp as pmgvasp
        pmgkpt = pmgvasp.Kpoints.from_file(filename)
        kpoints = {}
        kpoints['mesh'] = pmgkpt.kpts[0]
        kpoints['shift'] = pmgkpt.kpts_shift
        kpoints['style'] = pmgkpt.style.name
        return kpoints

    if filename is not None and kpoints_string is not None:
        raise ValueError("both 'filename' and 'kpoints_string' are input")
    if filename is not None:
        kpoints = _shape_kpoints_file(filename)
    elif kpoints_string is not None:
        kpoints = _shape_input_string(kpoints_string)
    else:
        raise ValueError("both 'filename' and 'kpoints_string' are None")



def import_StructureData(filename, filetype, comment):
    """
    import StructureData

        Parameters
        ----------
        filename : str
            input file name
        filetype : int, default var
            file type of 'filename'
            currently supported 'cif' or 'poscar'
        comment : str

        Notes
        -----
        occupancy_tolerance = 1.
        - If total occupancy of a site is between 1 and
          occupancy_tolerance, the occupancies will be scaled down to 1.

        site_tolerance = 1e-4
        - This tolerance is used to determine if two sites are sitting
          in the same position, in which case they will be combined to
          a single disordered site.

        primitive = False
        - When the input cif file convert to the pymatgen structure,
          do not try to find primitive.

        Raises
        ------
        ValueError
            specified filetype is not supported
    """
    from aiida.orm.nodes.data import StructureData

    occupancy_tolerance = 1.
    site_tolerance = 1e-4
    primitive = False

    if filetype == 'cif':
        from pymatgen.io import cif as pmgcif
        cif = pmgcif.CifParser(filename,
                               occupancy_tolerance=occupancy_tolerance,
                               site_tolerance=site_tolerance)
        pmgstruct = cif.get_structures(primitive=primitive)[0]
    elif filetype == 'poscar':
        from pymatgen.io.vasp import inputs as pmginputs
        poscar = pmginputs.Poscar.from_file(filename)
        pmgstruct = poscar.structure
    else:
        raise ValueError("specified filetype is not supported")

    structure = StructureData(pymatgen_structure=pmgstruct)
    structure.store()
    structure.add_comment(comment)
    print("structure data imported")
    print("pk : %s \n" % str(structure.pk))
    print("# to check the imported structure")
    print("verdi data structure export %s \n" % str(structure.pk))
    print("# to check the comment")
    print("verdi comment show %s" % str(structure.pk))


@with_dbenv()
def main(filename, filetype, kpoints_string, comment):
    """
    import data with comment

        Parameters
        ----------
        filename : str
            input file name
        filetype : int, default var
            file type of 'filename'
            currently supported 'cif' or 'poscar'
        kpoints_string : str
            input kpoints string
        comment : str
            comment

        Raises
        ------
        ValueError
            specified filetype is not supported
    """
    # run mode
    if args.kpoints is not None:
        # kpoints = _shape_input_kpoints(args.kpoints)
        run_mode = 'kpoints'
    else:
        run_mode = _detect_run_mode(filetype)
    print("runmode : %s \n" % run_mode)

    # import
    if run_mode == 'kpoints':
        import_KpointsData(filename=filename, kpoints_string=kpoints_string)
    if run_mode == 'structure':
        import_StructureData(filename, filetype, comment)


if __name__ == '__main__':
    print("# inputs")
    print("filename : %s" % str(args.filename))
    print("filetype : %s" % str(args.filetype))
    print("kpoints  : %s" % str(args.kpoints))
    print("comment  : %s \n" % str(args.comment))
    main(filename=args.filename,
         filetype=args.filetype,
         kpoints_string=args.kpoints,
         comment=args.comment)
