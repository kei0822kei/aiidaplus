#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
plot
----
provide various kinds of plot
"""

import numpy as np
from copy import deepcopy
from matplotlib import pyplot as plt
import mpl_toolkits.axes_grid1
from phonopy.phonon.band_structure import BandPlot as PhonopyBandPlot
from phonopy.phonon.dos import TotalDos as PhonopyTotalDos
from phonopy.phonon.band_structure import get_band_qpoints_and_path_connections
from mpl_toolkits.axes_grid1 import ImageGrid


# plt.rcParams["font.size"] = 18

DEFAULT_COLORS = ['r', 'b', 'm', 'y', 'g', 'c']
DEFAULT_COLORS.extend(plt.rcParams['axes.prop_cycle'].by_key()['color'])
DEFAULT_MARKERS = ['o', 'v', ',', '^', 'h', 'D', '<', '*', '>', 'd']

def decorate_string_for_latex(string):
    """
    decorate strings for latex
    """
    if string == 'GAMMA':
        decorated_string = "$" + string.replace("GAMMA", r"\Gamma") + "$"
    elif string == 'SIGMA':
        decorated_string = "$" + string.replace("SIGMA", r"\Sigma") + "$"
    elif string == 'DELTA':
        decorated_string = "$" + string.replace("DELTA", r"\Delta") + "$"
    elif string == 'LAMBDA':
        decorated_string = "$" + string.replace("LAMBDA", r"\Lambda") + "$"
    else:
        decorated_string = r"$\mathrm{%s}$" % string
    return decorated_string

def line_chart(ax, xdata, ydata, xlabel, ylabel, label=None, alpha=1., **kwargs):
    """
    plot line chart in ax

    Note:
        kwargs: c, marker, facecolor
    """
    if 'c' in kwargs.keys():
        c = kwargs['c']
    else:
        c_num = len(ax.get_lines()) % len(DEFAULT_COLORS)
        c = DEFAULT_COLORS[c_num]

    if 'marker' in kwargs.keys():
        marker = kwargs['marker']
    else:
        marker_num = len(ax.get_lines()) % len(DEFAULT_MARKERS)
        marker = DEFAULT_MARKERS[marker_num]

    if 'facecolor' in kwargs.keys():
        facecolor = kwargs['facecolor']
    else:
        facecolor_num = len(ax.get_lines()) % 2
        if facecolor_num == 0:
            facecolor = 'white'
        else:
            facecolor = c

    raw = np.array([xdata, ydata])
    idx = np.array(xdata).argsort()
    sort = raw[:,idx]
    ax.plot(sort[0,:], sort[1,:], linestyle='--', linewidth=0.5, c=c, alpha=alpha, label=label)
    ax.scatter(sort[0,:], sort[1,:], facecolor=facecolor, marker=marker, edgecolor=c, alpha=alpha)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

def line_chart_group(ax, xdata, ydata, xlabel, ylabel, gdata, glabel, **kwargs):
    uniques = np.unique(gdata)
    for unique in uniques:
        idxes = [ idx for idx in range(len(gdata)) if np.isclose(gdata[idx], unique) ]
        label = '{}: {}'.format(glabel, unique)
        line_chart(ax, np.array(xdata)[idxes], np.array(ydata)[idxes], xlabel, ylabel, label, **kwargs)
    ax.legend()

def line_chart_group_trajectory(ax, xdata, ydata, xlabel, ylabel, gdata, glabel, tdata=None, **kwargs):
    uniques_ = np.unique(gdata)
    for j, unique_ in enumerate(uniques_):
        c = DEFAULT_COLORS[j%len(DEFAULT_COLORS)]
        uniques = np.unique(tdata)
        minimum = 0.3
        alphas = [ minimum+(1.-minimum)/(len(uniques)-1)*i for i in range(len(uniques)) ]
        for i, unique in enumerate(uniques):
            marker = DEFAULT_MARKERS[i]
            idxes = [ idx for idx in range(len(gdata)) if np.isclose(gdata[idx], unique_) and np.isclose(tdata[idx], unique) ]
            if i == len(uniques)-1:
                label = '{}: {}'.format(glabel, unique_)
                line_chart(ax, np.array(xdata)[idxes], np.array(ydata)[idxes], xlabel, ylabel, label, alpha=alphas[i], c=c, marker=marker, **kwargs)
            else:
                line_chart(ax, np.array(xdata)[idxes], np.array(ydata)[idxes], xlabel, ylabel, alpha=alphas[i], c=c, marker=marker, **kwargs)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0, fontsize=12)

def shift_energy_plot(ax, shifts, energies, natoms, a, b, ev_range=4):
    from scipy import stats
    from scipy import interpolate
    from mpl_toolkits.mplot3d import Axes3D
    ax.set_aspect('equal')
    # ene_atom = energies / natoms
    energies = energies
    shifts = np.array(shifts)
    shifts = np.where(shifts>0.5, shifts-1, shifts)
    xyz = np.hstack((shifts, energies.reshape(energies.shape[0],1)))
    x1 = xyz[np.isclose(xyz[:,0], 0.5)] + np.array([-1,0,0])
    y1 = xyz[np.isclose(xyz[:,1], 0.5)] + np.array([0,-1,0])
    xy1 = x1[np.isclose(x1[:,1], 0.5)] + np.array([0,-1,0])
    full_xyz = np.vstack((xyz, x1, y1, xy1))
    sort_ix = np.argsort((len(np.unique(shifts[:,0]))+1)*full_xyz[:,0] + full_xyz[:,1])
    sort_xyz = full_xyz[sort_ix]

    xy = sort_xyz[:,:2]
    z = sort_xyz[:,2]

    x = y = np.linspace(-0.5, 0.5, 500)
    X, Y = np.meshgrid(x, y)

    # i_Z = interpolate.griddata(xy*np.array([a,b]), z, (X*a, Y*b), method='cubic')
    i_Z = interpolate.griddata(xy*np.array([a,b]), z, (X*a, Y*b), method='linear')

    # plot interpolation Z
    # im = ax.pcolormesh(X*a, Y*b, i_Z, cmap="jet_r", vmax=min(min(energies)*0.85, max(energies)))
    # im = ax.pcolormesh(Y*b, X*a, i_Z, cmap="jet_r", vmin=min(energies), vmax=min(energies)+1)
    # im = ax.pcolormesh(Y*b, X*a, i_Z, cmap="jet_r", vmin=min(energies), vmax=min(energies)*0.95)
    im = ax.pcolormesh(Y*b, X*a, i_Z, cmap="jet_r", vmin=min(energies), vmax=min(energies)+ev_range)
    divider = mpl_toolkits.axes_grid1.make_axes_locatable(ax)
    cax = divider.append_axes('right', '5%', pad='3%')
    # im = ax.imshow(Z, interpolation='none')
    # plt.colorbar(im, ax=ax, fraction=0.20, label='energy per atom [eV/atom]',)
    plt.colorbar(im, ax=ax, cax=cax, label='total energy [eV]')
    # ax.scatter(xy[:,0]*a, xy[:,1]*b, c='k')
    ax.scatter(xy[:,1]*b, xy[:,0]*a, c='k')
    for i in np.unique(shifts[:,1]):
        ax.axvline(i*b, c='k', linestyle='--')
    for i in np.unique(shifts[:,0]):
        ax.axhline(i*a, c='k', linestyle='--')
    ax.set_title("shift energy")
    ax.set_xlabel("y shift [angstrom]")
    ax.set_ylabel("x shift [angstrom]")


class TotalDosPlot(PhonopyTotalDos):

    def __init__(self,
                 ax,
                 mesh_object,
                 sigma=None,
                 use_tetrahedron_method=False,
                 ):
        """
        total dos plot

        Args:
            sigma : float, optional
                Smearing width for smearing method. Default is None
            use_tetrahedron_method : float, optional
                Use tetrahedron method when this is True. When sigma is set,
                smearing method is used.
        """
        self.ax = ax
        super().__init__(mesh_object=mesh_object,
                         sigma=sigma,
                         use_tetrahedron_method=use_tetrahedron_method)

    def plot(self,
             ax,
             c,
             alpha,
             linestyle,
             linewidth,
             xlabel=None,
             ylabel=None,
             draw_grid=True,
             flip_xy=False,
             label=None,
             ):
        if flip_xy:
            _xlabel = 'Density of states'
            _ylabel = 'Frequency'
        else:
            _xlabel = 'Frequency'
            _ylabel = 'Density of states'

        if xlabel is not None:
            _xlabel = xlabel
        if ylabel is not None:
            _ylabel = ylabel

        _plot_total_dos(ax,
                        self._frequency_points,
                        self._dos,
                        c=c,
                        alpha=alpha,
                        linestyle=linestyle,
                        linewidth=linewidth,
                        freq_Debye=self._freq_Debye,
                        Debye_fit_coef=self._Debye_fit_coef,
                        xlabel=_xlabel,
                        ylabel=_ylabel,
                        draw_grid=draw_grid,
                        flip_xy=flip_xy,
                        label=label,
                        )

def _plot_total_dos(ax,
                    frequency_points,
                    total_dos,
                    c,
                    alpha,
                    linewidth,
                    linestyle,
                    freq_Debye=None,
                    Debye_fit_coef=None,
                    xlabel=None,
                    ylabel=None,
                    draw_grid=True,
                    flip_xy=False,
                    label=None,
                    ):
    ax.xaxis.set_ticks_position('both')
    ax.yaxis.set_ticks_position('both')
    ax.xaxis.set_tick_params(which='both', direction='in')
    ax.yaxis.set_tick_params(which='both', direction='in')

    if freq_Debye is not None:
        freq_pitch = frequency_points[1] - frequency_points[0]
        num_points = int(freq_Debye / freq_pitch)
        freqs = np.linspace(0, freq_Debye, num_points + 1)

    if flip_xy:
        ax.plot(total_dos, frequency_points, c=c, alpha=alpha, linewidth=linewidth, linestyle=linestyle, label=label)
        if freq_Debye:
            ax.plot(np.append(Debye_fit_coef * freqs**2, 0),
                    np.append(freqs, freq_Debye), 'b-', linewidth=1)
    else:
        ax.plot(frequency_points, total_dos, c=c, alpha=alpha, linewidth=linewidth, linestyle=linestyle, label=label)
        if freq_Debye:
            ax.plot(np.append(freqs, freq_Debye),
                    np.append(Debye_fit_coef * freqs**2, 0), 'b-', linewidth=1)

    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)

    ax.grid(draw_grid)

def total_doses_plot(ax,
                     phonons,
                     mesh,
                     sigma=None,
                     freq_min=None,
                     freq_max=None,
                     freq_pitch=None,
                     use_tetrahedron_method=False,
                     cs=None,
                     alphas=None,
                     linewidths=None,
                     linestyles=None,
                     draw_grid=True,
                     flip_xy=False,
                     labels=None,
                     **kwargs):
    if cs is None:
        cs = [ DEFAULT_COLORS[i%len(DEFAULT_COLORS)] for i in range(len(phonons)) ]
    if alphas is None:
        alphas = [ 1. ] * len(phonons)
    if linestyles is None:
        linestyles = [ 'solid' ] * len(phonons)
    if linewidths is None:
        linewidths = [ 1. ] * len(phonons)
    if labels is None:
        labels = [None] * len(phonons)

    total_doses = []
    for phonon in phonons:
        phonon.set_mesh(mesh)
        total_dos = TotalDosPlot(ax,
                                 mesh_object=phonon.mesh,
                                 sigma=sigma,
                                 use_tetrahedron_method=use_tetrahedron_method)
        total_dos.set_draw_area(freq_min, freq_max, freq_pitch)
        total_dos.run()
        total_doses.append(total_dos)

    for i, total_dos in enumerate(total_doses):
        total_dos.plot(ax=ax,
                       c=cs[i],
                       alpha=alphas[i],
                       linewidth=linewidths[i],
                       linestyle=linestyles[i],
                       draw_grid=draw_grid,
                       flip_xy=flip_xy,
                       label=labels[i]
                       )


class BandsPlot(PhonopyBandPlot):
    """
    band structure plot class
    """
    def __init__(self,
                 fig,
                 phonons,
                 band_labels=None,
                 segment_qpoints=None,
                 is_auto=False,
                 overwrite_phonons=False,
                 xscale=20,
                 npoints=51,
                 with_dos=False,
                 mesh=None):
        """
        band plot
        """
        self.fig = fig
        # not working now
        if overwrite_phonons:
            self.phonons = phonons
        else:
            self.phonons = deepcopy(phonons)
        self.band_labels = None
        self.connections = None
        self.axes = None
        self.mesh = mesh
        self.with_dos = with_dos
        self.npoints = npoints
        self._run_band(band_labels,
                       segment_qpoints,
                       is_auto,
                       self.npoints)
        self._set_axs()
        super().__init__(axs=self.axs)
        self.xscale = xscale
        self._set_frame()

    def _revise_distances(self, distances, base_distances):
        segment_lengths = []
        for ds in [distances, base_distances]:
            lengths = []
            init = 0
            for d in ds:
                lengths.append(d[-1]-init)
                init = d[-1]
            segment_lengths.append(lengths)
        ratios = np.array(segment_lengths)[0] /  np.array(segment_lengths)[1]
        revised = []
        seg_start = 0
        for i, distance in enumerate(distances):
            if i == 0:
                revised.append(distance / ratios[i])
            else:
                revised.append(seg_start+(distance-distances[i-1][-1]) / ratios[i])
            seg_start = revised[-1][-1]
        return revised

    def _set_axs(self):
        n = len([x for x in self.phonons[0].band_structure.path_connections if not x])
        if self.with_dos:
            n += 1
        self.axs = ImageGrid(self.fig, 111,  # similar to subplot(111)
                             nrows_ncols=(1, n),  # n is the number of figures
                             axes_pad=0.11,   # pad between axes in inch.
                             add_all=True,
                             label_mode="L")

    def _set_frame(self):
        self.decorate(self.band_labels,
                      self.connections,
                      self.phonons[0].band_structure.get_frequencies(),
                      self.phonons[0].band_structure.get_distances())

    def _run_band(self,
                  band_labels,
                  segment_qpoints,
                  is_auto,
                  npoints):
        for i, phonon in enumerate(self.phonons):
            if i == 0:
                _run_band_calc(phonon=phonon,
                               band_labels=band_labels,
                               segment_qpoints=segment_qpoints,
                               is_auto=is_auto,
                               npoints=npoints)
                base_primitive_matrix = phonon.get_primitive_matrix()
                qpt = phonon.band_structure.qpoints
                con = phonon.band_structure.path_connections
                segment_qpoints = []
                l = []
                for i in range(len(qpt)):
                    if con[i]:
                        l.append(qpt[i][0])
                    else:
                        l.extend([qpt[i][0], qpt[i][-1]])
                        segment_qpoints.append(np.array(l))
                        l = []
                self.segment_qpoints = segment_qpoints

            else:
                primitive_matrix = phonon.get_primitive_matrix()
                fixed_segment_qpoints = []
                for segment in self.segment_qpoints:
                    fixed_segment = \
                            np.dot(primitive_matrix.T,
                                   np.dot(np.linalg.inv(base_primitive_matrix.T),
                                          segment.T)).T
                    fixed_segment_qpoints.append(fixed_segment)
                fixed_segment_qpoints = np.array(fixed_segment_qpoints)
                _run_band_calc(phonon=phonon,
                               band_labels=self.phonons[0].band_structure.labels,
                               segment_qpoints=fixed_segment_qpoints,
                               is_auto=False,
                               npoints=npoints)

        if is_auto:
            self.band_labels = self.phonons[0].band_structure.labels
        else:
            self.band_labels = [ decorate_string_for_latex(label) for label in band_labels ]
        self.connections = self.phonons[0].band_structure.path_connections

    def plot_bands(self, cs=None, alphas=None, linestyles=None, linewidths=None, labels=None):
        """
        plot band, **kwargs is passed for plotting with matplotlib

        Note:
            currently suppored **kwargs
            - 'cs'
            - 'alphas'
            - 'linestyles'
            - 'linewidths'
            - 'labels'
        """
        def _plot(distances, frequencies, connections, is_decorate,
                  c, alpha, linestyle, linewidth, label):
            count = 0
            distances_scaled = [d * self.xscale for d in distances]
            for d, f, cn in zip(distances_scaled,
                                frequencies,
                                connections):
                ax = self.axs[count]
                ax.plot(d, f, c=c, alpha=alpha, linestyle=linestyle,
                             linewidth=linewidth, label=label)
                if is_decorate:
                    ax.axvline(d[-1], c='k', linestyle='dotted', linewidth=0.5)
                if not cn:
                    count += 1

        if cs is None:
            cs = [ DEFAULT_COLORS[i%len(DEFAULT_COLORS)] for i in range(len(self.phonons)) ]
        if alphas is None:
            alphas = [ 1. ] * len(self.phonons)
        if linestyles is None:
            linestyles = [ 'solid' ] * len(self.phonons)
        if linewidths is None:
            linewidths = [ 1. ] * len(self.phonons)
        if labels is None:
            labels = [ None ] * len(self.phonons)

        for i, phonon in enumerate(self.phonons):
            distances = phonon.band_structure.get_distances()
            frequencies = phonon.band_structure.get_frequencies()
            if i == 0:
                _plot(distances, frequencies, self.connections, is_decorate=True,
                      c=cs[i], alpha=alphas[i], linestyle=linestyles[i], linewidth=linewidths[i], label=labels[i])
                base_distances = deepcopy(distances)
            else:
                distances = self._revise_distances(distances, base_distances)
                _plot(distances, frequencies, self.connections, is_decorate=False,
                      c=cs[i], alpha=alphas[i], linestyle=linestyles[i], linewidth=linewidths[i], label=labels[i])

            if self.with_dos:
                # total_doses_plot(ax=self._axs[-1],
                #                  phonons=self.phonons,
                #                  mesh=self.mesh,
                #                  cs=cs,
                #                  alphas=alphas,
                #                  linewidths=linewidths,
                #                  linestyles=linestyles,
                #                  flip_xy=True,
                #                  draw_grid=False,
                #                  labels=labels,
                #                  )
                if i == 0:
                    total_doses_plot(ax=self._axs[-1],
                                     phonons=self.phonons,
                                     mesh=self.mesh,
                                     cs=cs,
                                     alphas=alphas,
                                     linewidths=linewidths,
                                     linestyles=linestyles,
                                     flip_xy=True,
                                     draw_grid=False,
                                     labels=labels,
                                     )
                    xlim = self._axs[-1].get_xlim()
                    ylim = self._axs[-1].get_ylim()
                    aspect = (xlim[1] - xlim[0]) / (ylim[1] - ylim[0]) * 3
                    self._axs[-1].set_aspect(aspect)
                    self._axs[-1].axhline(y=0, linestyle=':', linewidth=0.5, color='b')
                    self._axs[-1].set_xlim((0, None))
                else:
                    total_doses_plot(ax=self._axs[-1],
                                     phonons=self.phonons,
                                     mesh=self.mesh,
                                     cs=cs,
                                     alphas=alphas,
                                     linewidths=linewidths,
                                     linestyles=linestyles,
                                     flip_xy=True,
                                     draw_grid=False,
                                     labels=None,
                                     )
        self._axs[-1].legend()

def _run_band_calc(phonon,
                   band_labels=None,
                   segment_qpoints=None,
                   is_auto=False,
                   npoints=51):
    if is_auto:
        print("# band path is set automalically")
        phonon.auto_band_structure(plot=False,
                               write_yaml=False,
                               with_eigenvectors=False,
                               with_group_velocities=False,
                               npoints=npoints)
    else:
        qpoints, path_connections = get_band_qpoints_and_path_connections(
                segment_qpoints, npoints=npoints,
                rec_lattice=np.linalg.inv(phonon.get_primitive().cell))
        phonon.run_band_structure(paths=qpoints,
                                  with_eigenvectors=True,
                                  with_group_velocities=False,
                                  is_band_connection=False,
                                  path_connections=path_connections,
                                  labels=band_labels,
                                  is_legacy_plot=False)
        phonon.write_yaml_band_structure()

def band_plot(fig,
              phonon,
              with_dos=False,
              mesh=None,
              band_labels=None,
              segment_qpoints=None,
              is_auto=False,
              c='r',
              alpha=1.,
              linewidth=1.,
              linestyle='solid',
              ):
    bands_plot(fig,
               [phonon],
               with_dos=with_dos,
               mesh=mesh,
               band_labels=band_labels,
               segment_qpoints=segment_qpoints,
               is_auto=is_auto,
               xscale=20,
               cs=[c],
               alphas=[alpha],
               linewidths=[linewidth],
               linestyles=[linestyle],
               labels=None,
               )

def bands_plot(fig,
               phonons,
               with_dos=False,
               mesh=None,
               band_labels=None,
               segment_qpoints=None,
               is_auto=False,
               xscale=20,
               npoints=51,
               cs=None,
               alphas=None,
               linewidths=None,
               linestyles=None,
               labels=None,
               ):
    bp = BandsPlot(fig,
                   phonons,
                   with_dos=with_dos,
                   mesh=mesh,
                   band_labels=band_labels,
                   segment_qpoints=segment_qpoints,
                   is_auto=is_auto,
                   xscale=xscale,
                   npoints=npoints)
    bp.plot_bands(cs=cs,
                  alphas=alphas,
                  linestyles=linestyles,
                  linewidths=linewidths,
                  labels=labels)

def get_plot_properties_from_trajectory(plot_nums:int,
                                        base_color:str='r'):
    """
    arg 'plot_nums' is the number of plots
    return (cs, alphas, linewidths, linestyles)
    """
    alphas = [ 1. ]
    linewidths = [ 1.5 ]
    linestyles = [ 'dashed' ]
    alphas.extend([ 0.3 for _ in range(plot_nums-2) ])
    linewidths.extend([ 1. for _ in range(plot_nums-2) ])
    linestyles.extend([ 'dotted' for _ in range(plot_nums-2) ])
    alphas.append(1.)
    linewidths.append(1.5)
    linestyles.append('solid')
    cs = [ base_color for _ in range(plot_nums) ]
    return (cs, alphas, linewidths, linestyles)
