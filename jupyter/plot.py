#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# plot various figures
###############################################################################

"""
plot various figures

    def dispersion
"""

### import basic modules import sys
import math
import re
import numpy as np
import sys
import matplotlib as mpl
import matplotlib.pyplot as plt
from scipy import stats
from phonaly import file_io

### variables
color_lst = ['g', 'c', 'm', 'y', 'k', 'b']

def _match(arg_lst, element, match_type='full', inverse=False):
    """
      input object  : list, str or int or float, match_type = 'full'(default) or 'part',
                      inverse = True or False(default)
      output object : list
      description   : return matched address list
      option        : match_type => you can choose match type
                      inverse => if True, you can get inverse_list
      example       : match([2, 5, 'a', 4, 'a'], 'a') = [2, 4]
    """
    if match_type == 'full':
        matched_address_lst = [i for i, x
                               in enumerate(arg_lst) if element == x]
    elif match_type == 'part':
        matched_address_lst = [i for i, x
                               in enumerate(arg_lst) if element in x]
    else:
        print("match_type is 'full' or 'part'")
        sys.exit(1)
    if inverse:
        return inverse_index(len(arg_lst), matched_address_lst)
    else:
        return matched_address_lst

def dispersion(ax, yaml_file='band.yaml', mode=None, axis=False,
               ymin=None, ymax=None, fontsize=10, color='r'):
    """
    input         : ax;  ex) ax = fig.add_subplot(111)
                    yaml_file; str => default ('band.yaml')
    output        : ax
    options       : axis = False => if True, return (xmin, xmax, ymin, ymax)
                    fig setting
                    mode = None (default) or 'ac_op' or 'separate'
                             'ac_op' => acoustic and optical
                             'separate' => each branch
                    ymin=None, ymax=None, fontsize=10
    description   : return ax which is painted phonon dispersion curve
    """
    ### get data
    yam = file_io.Band(yaml_file)
    (distances, frequencies, segment_nqpoint, labels) = yam.dispersion_data()

    ### plot dispersion curves
    end_points = [0, ]
    for nq in segment_nqpoint:
        end_points.append(nq + end_points[-1])
    end_points[-1] -= 1
    segment_positions = distances[end_points]

    q = 0
    for j, nq in enumerate(segment_nqpoint):
        if mode == 'ac_op':
            ax.plot(distances[q:(q + nq)],
                      frequencies[q:(q + nq), :3], color='b')
            ax.plot(distances[q:(q + nq)],
                      frequencies[q:(q + nq), 3:], color='g')

        elif mode == 'separate':
            for i in range(frequencies.shape[1]):
                ax.plot(distances[q:(q + nq)],
                frequencies[q:(q + nq), i],
                color=color_lst[i])

        else:
            ax.plot(distances[q:(q + nq)],
            frequencies[q:(q + nq)],
            color=color)
        q += nq

    ### labels
    if all(x is None for x in labels):
        labels_at_ends = None
    else:
        labels_at_ends = [labels[n] for n in end_points]

    if '\Gamma' in labels_at_ends:
        gamma_lst = _match(labels_at_ends, '\Gamma')
        for i in gamma_lst:
            labels_at_ends[i] = '$\Gamma$'

    ax.set_xticks(segment_positions)
    ax.set_xticklabels(labels_at_ends)

    ### vertical line
    for position in segment_positions:
        ax.axvline(x=position, color='black', linestyle='dotted', linewidth=1)

    ### y=0 plot
    ax.hlines(y=0, xmin=segment_positions[0], xmax=segment_positions[-1],
              linestyle=':')

    ### setting
    ax.set_xlim(segment_positions[0], segment_positions[-1])
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel('Wave vector', fontsize=fontsize)
    ax.set_ylabel('Phonon frequency(THz)', fontsize=fontsize)

    ### axis
    if axis:
        return ax.axis()

def dos(ax, dos_dat_file='total_dos.dat', axis=False, color='r', inverse=False, normalize=False,
        xmax=None, ymin=None, ymax=None, ylabel=True, fontsize=10, zeroline=False):
    """
    total density of states

        Parameters
        ----------
        ax : matplotlib.axes._subplots.AxesSubplot
            ex) fig = plt.figure()
                ax = fig.add_subplot(111)
        dos_dat_file : str, default 'total_dos.dat'
        axis : bool, default False
            see 'Returns'
        xmax, ymin, ymax : float, default None
        ylabel : bool, default True
            if False, ylabel is removed
        color : str, default 'r'
        fontsize : int, default 10
        zeroline : bool, default True
            if False, zeroline does not show

        Returns
        -------
        ax.axes() : tuple
            if axis=True, return (xmin, xmax, ymin, ymax)
    """
    ### read data
    t_dos = file_io.Total_dos(dos_dat_file)

    ### plot total dos
    if normalize is None:
        if inverse:
            ax.plot(t_dos.data[:, 0], t_dos.data[:, 1], color=color)
        else:
            ax.plot(t_dos.data[:, 1], t_dos.data[:, 0], color=color)
    else:
        if inverse:
            ax.plot(t_dos.data[:, 0] / normalize, t_dos.data[:, 1], color=color)
        else:
            ax.plot(t_dos.data[:, 1] / normalize, t_dos.data[:, 0], color=color)

    if xmax == None:
        xmax = max(t_dos.data[:, 1]) * 1.1

    ### y = 0 plot
    if zeroline:
        ax.hlines(y=0, xmin=0, xmax=xmax, linestyle=':')

    ### setting
    ax.set_xlim(0, xmax)
    ax.set_ylim(ymin, ymax)
    if inverse:
        ax.set_ylabel('DOS (/THz)', fontsize=fontsize)
        ax.set_xlabel('Phonon frequency (THz)', fontsize=fontsize)
    else:
        ax.set_xlabel('DOS (/THz)', fontsize=fontsize)
        ax.set_ylabel('Phonon frequency (THz)', fontsize=fontsize)

    ### ylabel
    if ylabel == False:
        ax.set_yticklabels([])
        ax.set_ylabel('')

    ### axis
    if axis:
        return ax.axis()

def pdos(ax, pdos_dat_file='partial_dos.dat', pos_file='POSCAR-unitcell',
         pdos_conf='pdos-m.conf', axis=False, xmax=None, ymin=None, ymax=None, ylabel=True,
         fontsize=10, linestyle='--'):
    """
    input         : ax;  ex) ax = fig.add_subplot(111)
                    pdos_dat_file; str => default ('partial_dos.dat')
                    pos_file; str => default ('POSCAR-unitcell')
                    pdos_conf; str => default ('pdos.conf')
    output        : ax
    options       : axis = False => if True, return (xmin, xmax, ymin, ymax)
                    fig setting
                      ymin=None, ymax=None, ylabel=True, fontsize=10,
                      linestyle=':'
    description   : return ax which is painted partial DOS
    """
    ### color
    pdos_color_lst = ['purple', 'c', 'green', 'blue']

    ### read data
    p_dos = file_io.Partial_dos(pdos_dat_file)

    ### get the elements from pos_file
    with open(pos_file) as f:
        lines = f.readlines()
    ele_lst = lines[5].split()
    elenum = len(ele_lst)

    ### get the number of the same compounds from pdos.conf
    with open(pdos_conf) as f:
        lines = f.readlines()
    for line in lines:
        if line.find('PDOS')==0:
            pdos_line = line
    divide = re.split("[,=]", pdos_line)
    num_lst = []
    for i in range(elenum):
        num_lst.append(len(divide[i+1].split()))

    ### plot partial dos
    dataline = 0
    data_max = 0
    for i in range(elenum):
        dataline = dataline + num_lst[i]
        p_data =p_dos.data[:, dataline] * num_lst[i]
        #ax.plot(p_data, data[:, 0], label=ele_lst[i],
        #        linestyle=linestyle, color=pdos_color_lst[i])
        ax.fill_between(p_data, p_dos.data[:, 0], label=ele_lst[i], alpha=0.7,
                linestyle=linestyle, facecolor=pdos_color_lst[i])
        if data_max < max(p_data):
            data_max = max(p_data)

    ### y=0 plot
    if xmax == None:
        xmax = data_max * 1.1
    ax.hlines(y=0, xmin=0, xmax=xmax, linestyle=':')

    ### setting
    ax.set_xlim(0, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel('PDOS (/THz)', fontsize=fontsize)
    ax.set_ylabel('Phonon frequency (THz)', fontsize=fontsize)
    if ylabel == False:
        ax.set_yticklabels([])
        ax.set_ylabel('')
    ax.legend(fontsize=fontsize, loc="upper right")

    ### axis
    if axis:
        return ax.axis()

    # return p_data, data[:, 0]

def kaccum(ax, kaccum_dat_file, mode='kaccum', tensor='xx', T=300, axis=False, xmax=None,
           ymin=None, ymax=None, xlabel=True, ylabel=True, inverse=False, loc=None, linestyle='-',
           color='r', fontsize=10, zeroline=True):
    """
    plot the data which is read from the output data from phonopy-kaccum

        Parameters
        ----------
        ax : matplotlib.axes._subplots.AxesSubplot
            ex) fig = plt.figure()
                ax = fig.add_subplot(111)
        kaccum_dat_file : str
            output file from phonopy-kaccum
        mode : str, default 'kaccum'
            select 'kaccum' or 'per'
                'kaccum' -- cumulative
                'per' -- per frequency or so on
        tensor : str, default 'xx'
        T : int, default 300
        axis : bool, default False
            see 'Returns'
        xmax, ymin, ymax : float, default None
        ylabel : bool, default True
            if False, ylabel is removed
        inverse : bool, default False
            if True, xdata and ydata are exchanged
        linestyle : You can also specify 'linestyle="fill_between"'
                        default. '-'
        loc : str, default None
            legend loc ex) 'upper left'
        color : str, default 'r'
        fontsize : int, default 10
        zeroline : bool, default True
            if False, zeroline does not show

        Returns
        -------
        ax.axes() : tuple
            if axis=True, return (xmin, xmax, ymin, ymax)

        Raises
        ------
        ValueError
            'tensor' you specified does not exist
    """
    ### read data
    kcm = file_io.Kaccumdat(kaccum_dat_file)
    data = kcm.get_data(T=T)

    ### x_data
    if kcm.filetype == 'kappa' or \
       kcm.filetype == 'mfp' or \
       kcm.filetype == 'gv_x_gv':
        try:
            if mode == 'per':
                tensor = tensor + '_per'
            x_idx = kcm.columns.index(tensor)
        except:
            ValueError("%s does not exist" % tensor)
    else:
        if mode == 'per':
            x_idx = 2
        else:
            x_idx = 1

    if mode == 'per':
        # x_data = data[:,x_idx] * kcm.interval()
        # x_data = data[:,x_idx] / kcm.interval()
        x_data = data[:,x_idx]
        x_label = kcm.labels[2]
    else:
        x_data = data[:,x_idx]
        x_label = kcm.labels[1]
    x_column = kcm.columns[x_idx]
    if xmax == None:
        xmax = max(x_data) * 1.1

    ### y_data
    y_idx = 0
    y_data = data[:,y_idx]
    y_label = kcm.labels[0]
    if ymax == None:
        ymax = max(y_data) * 1.1
    if ymin == None:
        ymin = -ymax * 0.05

    ### plot
    if not inverse:
        ax.set_xlim(0, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel(x_label, fontsize=fontsize)
        ax.set_ylabel(y_label, fontsize=fontsize)
        if mode == 'per':
            if linestyle == 'fill_between':
                ax.fill_between(x_data, y_data, alpha=0.4, label=x_column, facecolor=color)
            else:
                ax.plot(x_data, y_data, label=x_column,
                        color=color, linestyle=linestyle)
        else:
            ax.plot(x_data, y_data, label=x_column, color=color, linestyle=linestyle)
    else:
        ax.set_xlim(0, ymax)
        ax.set_ylim(-xmax*0.05, xmax)
        ax.set_xlabel(y_label, fontsize=fontsize)
        ax.set_ylabel(x_label, fontsize=fontsize)
        if mode == 'per':
            if linestyle == 'fill_between':
                ax.fill_between(y_data, x_data, alpha=0.4, label=x_column, facecolor=color)
            else:
                ax.plot(y_data, x_data, label=x_column,
                        color=color, linestyle=linestyle)
        else:
            ax.plot(data[:, 0], data[:, x_idx], label=x_column, color=color, linestyle=linestyle)

    ### y = 0 plot
    if zeroline:
        if not inverse:
            ax.hlines(y=0, xmin=0, xmax=ax.axis()[1], linestyle=':')

    ### ylabel
    if ylabel == False:
        ax.set_yticklabels([])
        ax.set_ylabel('')
    if xlabel == False:
        ax.set_xticklabels([])
        ax.set_xlabel('')

    ### legend
    ax.legend(fontsize=fontsize, loc=loc)

    ### axis
    if axis:
        return ax.axis()

def qnorm_lifetime(fig, kappa_file, pos_file, T=300, fontsize=10, ymax=None):
    """
    input         : fig;  ex) fig = plt.figure()
                    kappa_file; str
                    pos_file; str => default ('POSCAR-unitcell')
                    T; int => default (T=300)
    output        : fig
    options       : fig setting
                      fontsize=10, ymax=50
    description   : return ax which is painted qnorm lifetime
    """
    ### read data
    kappa = file_io.Kappa(kappa_file)
    qnorm_arr = kappa.qnorm(pos_file)
    tau_arr = kappa.lifetime(T=T)

    ### plot
    band_num = tau_arr.shape[1]
    subplot_lst = [math.ceil(band_num / 3), 3]
    for i in range(band_num):
        ax = fig.add_subplot(subplot_lst[0], subplot_lst[1], i+1)
        ax.scatter(qnorm_arr[1:], tau_arr[1:, i], s=1)
        ax.set_title("band_"+str(i+1), fontsize=fontsize)
        ax.set_ylim(0, ymax)

    ### setting
    fig.text(0.5, 0.04, "q norm in reciprocal lattice space (/angstrom)",
             ha='center', va='center')
    fig.text(0.06, 0.5, "lifetime (ps)",
             ha='center', va='center', rotation='vertical')
    fig.subplots_adjust(wspace=0.3, hspace=0.4)

    if ymax != None:
        ylim([0, ymax])

    return fig

def kdeplot(ax, kappa_file, xdata='lifetime', T=300, scatter=True, smear=True,
            nbins=100, color='black', cmap='OrRd', inverse=False,
            axis=False, xmax=None, ymin=0, ymax=None, ylabel=True, fontsize=10):
    """
    input         : ax
                    kappa_file; str
                    nbins; int (default: nbins=100)
                    T; int (default: T=300)
    output        : ax
    options       : xdata => 'lifetime' or 'mean_free_path' or 'mean_free_path_myu'
                      (default: 'lifetime')
                    scatter (default: True)
                    smear (default: True)
                    color='black', cmap='OrRd'
                    axis = False => if True, return (xmin, xmax, ymin, ymax)
                    xmax=None, ymin=0, ylabel=True, fontsize=10
    """

    def collect_data(x_datas, frequencies, weights):
        freqs = []
        mode_prop = []

        for x_data, freq, w in zip(x_datas, frequencies, weights):
            ### remove index whose lifetime is 0
            condition = x_data > 0
            _x_data = np.extract(condition, x_data)
            _freq = np.extract(condition, freq)
            mode_prop += list(_x_data) * w
            freqs += list(_freq) * w

        x = np.array(mode_prop)
        y = np.array(freqs)

        return x, y

    def run_KDE(x, y, nbins):
        ### Running Gaussian-KDE by scipy
        x_min = 0
        x_max = x.max()
        y_min = 0
        y_max = y.max() * 1.1

        values = np.vstack([x.ravel(), y.ravel()])
        kernel = stats.gaussian_kde(values)

        xi, yi = np.mgrid[x_min:x_max:nbins*1j, y_min:y_max:nbins*1j]
        positions = np.vstack([xi.ravel(), yi.ravel()])
        zi = np.reshape(kernel(positions).T, xi.shape)

        return xi, yi, zi

    def plot(ax, xi, yi, zi, x, y, nbins, smear=True, scatter=True,
             xmax=None, ymin=0, ylabel=True, cmap='OrRd', color='black'):

        if smear:
            plt.pcolormesh(xi, yi, zi, cmap=cmap)
            plt.colorbar()

        if scatter:
            ax.scatter(x, y, s=0.01, c=color, marker='.')

        if xmax is None:
            ### plot 95 % of all the data
            xmax= np.sort(x)[int(len(np.sort(x)) * 0.95)]

        ax.set_xlim(xmin=0, xmax=xmax)
        #ax.set_ylim(ymin=ymin, ymax=y.max()*1.1)
        ax.set_ylim(ymin=ymin, ymax=ymax)


        if ylabel:
            ax.set_ylabel('Phonon frequency (THz)', fontsize=fontsize)

        else:
            ax.set_yticklabels([])
            ax.set_ylabel('')

        # ax.plot([xmax, 0], [0, 0], color="black", linestyle=":")


    ### get data
    kappa = file_io.Kappa(kappa_file)
    weights = kappa.data['weight']
    frequencies = kappa.data['frequency']

    if xdata == 'lifetime':
        x_datas = kappa.lifetime(cutoff=1e-8, T=T)
        ax.set_xlabel('Phonon Lifetime (ps)', fontsize=fontsize)

    elif xdata == 'mean_free_path':
        x_datas = kappa.mean_free_path()
        ax.set_xlabel('Mean free path ('+r'$\AA$'+')', fontsize=fontsize)

    elif xdata == 'mean_free_path_x':
        x_datas = np.abs(kappa.mean_free_path(vector=True)[:,:,0])
        ax.set_xlabel('Mean free path ('+r'$\AA$'+')', fontsize=fontsize)

    elif xdata == 'mean_free_path_y':
        x_datas = np.abs(kappa.mean_free_path(vector=True)[:,:,0])
        ax.set_xlabel('Mean free path ('+r'$\AA$'+')', fontsize=fontsize)

    elif xdata == 'mean_free_path_z':
        x_datas = np.abs(kappa.mean_free_path(vector=True)[:,:,2])
        ax.set_xlabel('Mean free path ('+r'$\AA$'+')', fontsize=fontsize)

    elif xdata == 'mean_free_path_z-x':
        x_datas = np.abs(kappa.mean_free_path(vector=True)[:,:,2]) - np.abs(kappa.mean_free_path(vector=True)[:,:,0])
        ax.set_xlabel('Mean free path ('+r'$\AA$'+')', fontsize=fontsize)

    elif xdata == 'mean_free_path_myu':
        x_datas = kappa.mean_free_path() * 10**-4
        ax.set_xlabel('Mean free path ('+r'myu'+')', fontsize=fontsize)

    else:
        print("arg xdata must be 'lifetime' or 'mean_free_path'")
        sys.exit(1)

    ### Run
    x, y = collect_data(x_datas, frequencies, weights)
    if smear:
        xi, yi, zi = run_KDE(x, y, nbins)
    else:
        xi, yi, zi = None, None, None

    if not inverse:
        plot(ax, xi, yi, zi, x, y, nbins, smear=smear, scatter=scatter, cmap=cmap,
             color=color, xmax=xmax, ymin=ymin, ylabel=ylabel)
    else:
        plot(ax, yi, xi, zi, y, x, nbins, smear=smear, scatter=scatter, cmap=cmap,
             color=color, xmax=xmax, ymin=ymin, ylabel=ylabel)

    ### axis
    if axis:
        return ax.axis()

def file2plot(ax, filename, xdata, ydata):
    """
    input         : ax;  ex) ax = fig.add_subplot(111)
                    filename;
                        ex)  # title
                             # xlabel
                             # ylabel
                             # column
                             # data
                                :
                                :
                    xdata = 'sampling_point' for example
                    ydata = 'xx' for exmaple
    output        : ax
    """
    data_dic = file_io.plotfile2data(filename)
    xline = data_dic['column_lst'].index(xdata)
    yline = data_dic['column_lst'].index(ydata)
    ax.plot(data_dic['data'][:,xline], data_dic['data'][:,yline], label=ydata)
    ax.legend()
    ax.set_xlabel(data_dic['xlabel'])
    ax.set_ylabel(data_dic['ylabel'])
    ax.set_title(data_dic['title'])

#     def plot(ax, xi, yi, zi, x, y, nbins, smear=True, scatter=True,
#              xmax=None, ymin=0, ylabel=True, cmap='OrRd', color='black'):
# 
#         if smear:
#             plt.pcolormesh(xi, yi, zi, cmap=cmap)
#             plt.colorbar()
# 
#         if scatter:
#             ax.scatter(x, y, s=0.01, c=color, marker='.')
# 
#         if xmax is None:
#             ### plot 95 % of all the data
#             xmax= np.sort(x)[int(len(np.sort(x)) * 0.95)]
# 
#         ax.set_xlim(xmin=0, xmax=xmax)
#         #ax.set_ylim(ymin=ymin, ymax=y.max()*1.1)
#         ax.set_ylim(ymin=ymin, ymax=ymax)
# 
# 
#         if ylabel:
#             ax.set_ylabel('Phonon frequency (THz)', fontsize=fontsize)
# 
#         else:
#             ax.set_yticklabels([])
#             ax.set_ylabel('')
# 
#         ax.plot([xmax, 0], [0, 0], color="black", linestyle=":")
# 
# 
#     ### get data
#     kappa = file_io.Kappa(kappa_file)
#     weights = kappa.data['weight']
#     frequencies = kappa.data['frequency']
# 
#     if xdata == 'lifetime':
#         x_datas = kappa.lifetime(cutoff=1e-8, T=T)
#         ax.set_xlabel('Phonon Lifetime (ps)', fontsize=fontsize)
# 
# 
#     elif xdata == 'mean_free_path':
#         x_datas = kappa.mean_free_path()
#         ax.set_xlabel('Mean free path ('+r'$\AA$'+')', fontsize=fontsize)
# 
#     elif xdata == 'mean_free_path_myu':
#         x_datas = kappa.mean_free_path() * 10**-4
#         ax.set_xlabel('Mean free path ('+r'myu'+')', fontsize=fontsize)
# 
#     else:
#         print("arg xdata must be 'lifetime' or 'mean_free_path'")
#         sys.exit(1)
# 
#     ### Run
#     x, y = collect_data(x_datas, frequencies, weights)
#     if smear:
#         xi, yi, zi = run_KDE(x, y, nbins)
#     else:
#         xi, yi, zi = None, None, None
#     plot(ax, xi, yi, zi, x, y, nbins, smear=smear, scatter=scatter, cmap=cmap,
#          color=color, xmax=xmax, ymin=ymin, ylabel=ylabel)
# 
#     ### axis
#     if axis:
#         return ax.axis()
