#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This script deals with structure
"""

import argparse
from aiida.cmdline.utils.decorators import with_dbenv
from pymatgen.io.phonopy import get_ph_bs_symm_line
import yaml


# argparse
def get_argparse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-b', '--bandfile',
                        type=str,
                        default=None,
                        help="input file name or structure pk")
    parser.add_argument('-j', '--jsonfile',
                        type=str,
                        default='phononwebsite.json',
                        help="json file for phonon website")
    args = parser.parse_args()
    return args


@with_dbenv()
def main(bandfile,
         jsonfile,
         ):

    with open(bandfile) as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)
    labels_dict = {}
    count = 0
    for i, label in enumerate(data['labels']):
        labels_dict[label[0]] = data['phonon'][count]['q-position']
        count += data['segment_nqpoint'][i]

    ph_bandsym = get_ph_bs_symm_line(bands_path=bandfile,
                                     labels_dict=labels_dict)
    try:
        ph_bandsym.write_phononwebsite(filename=jsonfile)
    except TypeError:
        raise RuntimeError("NOTE: Error occurs. Check eigenvectors are stored "
                           "in band.yaml")


if __name__ == '__main__':
    args = get_argparse()
    main(bandfile=args.bandfile,
         jsonfile=args.jsonfile,
         )
