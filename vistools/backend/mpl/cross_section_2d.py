################################################################################
# Copyright (c) 2014, Brookhaven Science Associates, Brookhaven National       #
# Laboratory. All rights reserved.                                             #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided that the following conditions are met:  #
#                                                                              #
# * Redistributions of source code must retain the above copyright notice,     #
#   this list of conditions and the following disclaimer.                      #
#                                                                              #
# * Redistributions in binary form must reproduce the above copyright notice,  #
#  this list of conditions and the following disclaimer in the documentation   #
#  and/or other materials provided with the distribution.                      #
#                                                                              #
# * Neither the name of the European Synchrotron Radiation Facility nor the    #
#   names of its contributors may be used to endorse or promote products       #
#   derived from this software without specific prior written permission.      #
#                                                                              #
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"  #
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE    #
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE   #
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE    #
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR          #
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF         #
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS     #
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN      #
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)      #
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE   #
# POSSIBILITY OF SUCH DAMAGE.                                                  #
################################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .. import QtCore, QtGui
from six.moves import zip
from matplotlib.widgets import Cursor
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import NullLocator
import numpy as np

from . import AbstractMPLDataView
from .. import AbstractDataView2D


def _full_range(im, limit_args):
    """
    Plot the entire range of the image

    Parameters
    ----------
    im : ndarray
       image data, nominally 2D

    limit_args : object
       Ignored, here to match signature with other
       limit functions

    Returns
    -------
    climits : tuple
       length 2 tuple to be passed to `im.clim(...)` to
       set the color limits of a ColorMappable object.
    """
    return (np.min(im), np.max(im))


def _absolute_limit(im, limit_args):
    """
    Plot the image based on the min/max values in limit_args

    This function is a no-op and just return the input limit_args.

    Parameters
    ----------
    im : ndarray
        image data.  Ignored in this method

    limit_args : array
       (min_value, max_value)  Values are in absolute units
       of the image.

    Returns
    -------
    climits : tuple
       length 2 tuple to be passed to `im.clim(...)` to
       set the color limits of a ColorMappable object.

    """
    return limit_args


def _percentile_limit(im, limit_args):
    """
    Sets limits based on percentile.

    Parameters
    ----------
    im : ndarray
        image data

    limit_args : tuple of floats in [0, 100]
        upper and lower percetile values

    Returns
    -------
    climits : tuple
       length 2 tuple to be passed to `im.clim(...)` to
       set the color limits of a ColorMappable object.

    """
    return np.percentile(im, limit_args)


class CrossSection2DView(AbstractDataView2D, AbstractMPLDataView):
    """
    CrossSection2DView docstring
    """

    def __init__(self, fig, data_list, key_list, cmap=None, norm=None,
                 limit_func=None, limit_args=None):
        """
        Sets up figure with cross section viewer

        Parameters
        ----------
        fig : matplotlib.figure.Figure
            The figure object to build the class on, will clear
            current contents

        init_image : 2d ndarray
            The initial image

        cmap : str,  colormap, or None
           color map to use.  Defaults to gray

        clim_percentile : float or None
           percentile away from 0, 100 to put the max/min limits at
           ie, clim_percentile=5 -> vmin=5th percentile vmax=95th percentile

        norm : Normalize or None
           Normalization function to us
        """
        # call up the inheritance chain
        super(CrossSection2DView, self).__init__(fig=fig, data_list=data_list,
                                                 key_list=key_list, norm=norm,
                                                 cmap=cmap)
        # set some default behavior
        if limit_func is None:
            limit_func = _full_range
        if limit_args is None:
            limit_args = [0,100]
        if cmap is None:
            cmap = self._default_cmap

        # stash the input parameters not taken care of by parent classes
        self._limit_func = limit_func
        self._limit_args = limit_args

        # @tacaswell, what is this?
        self._active = True

        # work on setting up the mpl axes

        # extract the first image in the list
        init_image = self._data_dict[key_list[0]]

        # this needs to respect percentile
        # TODO: What does vlim stand for? @tacaswell?
        vlim = self._limit_func(init_image, self._limit_args)

        # make the main axes
        # (in matplotlib speak the 'main axes' is the 2d
        # image in the middle of the canvas)
        self._im_ax = fig.add_subplot(1, 1, 1)
        self._im_ax.set_aspect('equal')
        self._im_ax.xaxis.set_major_locator(NullLocator())
        self._im_ax.yaxis.set_major_locator(NullLocator())
        self._imdata = init_image
        self._im = self._im_ax.imshow(init_image, cmap=cmap, norm=norm,
                                      interpolation='none', aspect='equal')

        # make it dividable
        divider = make_axes_locatable(self._im_ax)

        # set up all the other axes
        # (set up the horizontal and vertical cuts)
        self._ax_h = divider.append_axes('top', .5, pad=0.1,
                                         sharex=self._im_ax)
        self._ax_h.yaxis.set_major_locator(NullLocator())
        self._ax_v = divider.append_axes('left', .5, pad=0.1,
                                         sharey=self._im_ax)
        self._ax_v.xaxis.set_major_locator(NullLocator())
        self._ax_cb = divider.append_axes('right', .2, pad=.5)
        # add the color bar
        self._cb = fig.colorbar(self._im, cax=self._ax_cb)

        # print out the pixel value
        def format_coord(x, y):
            numrows, numcols = self._imdata.shape
            col = int(x + 0.5)
            row = int(y + 0.5)
            if col >= 0 and col < numcols and row >= 0 and row < numrows:
                z = self._imdata[row, col]
                return "X: {x:d} Y: {y:d} I: {i:.2f}".format(x=col, y=row, i=z)
            else:
                return "X: {x:d} Y: {y:d}".format(x=col, y=row)

        self._im_ax.format_coord = format_coord

        # add the cursor
        self.cur = Cursor(self._im_ax, useblit=True, color='red', linewidth=2)

        # set the y-axis scale for the horizontal cut
        self._ax_h.set_ylim(*vlim)
        self._ax_h.autoscale(enable=False)

        # set the y-axis scale for the vertical cut
        self._ax_v.set_xlim(*vlim)
        self._ax_v.autoscale(enable=False)

        # add lines
        self._ln_v, = self._ax_v.plot(np.zeros(self._imdata.shape[0]),
                                np.arange(self._imdata.shape[0]), 'k-',
                                animated=True,
                                visible=False)

        self._ln_h, = self._ax_h.plot(np.arange(self._imdata.shape[1]),
                                np.zeros(self._imdata.shape[1]), 'k-',
                                animated=True,
                                visible=False)

        # backgrounds for blitting
        self._ax_v_bk = None
        self._ax_h_bk = None

        # stash last-drawn row/col to skip if possible
        self._row = None
        self._col = None

        # set up the call back for the updating the side axes
        def move_cb(event):
            if not self._active:
                return

            # short circuit on other axes
            if event.inaxes is not self._im_ax:
                return
            numrows, numcols = self._imdata.shape
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                self._ln_h.set_visible(True)
                self._ln_v.set_visible(True)
                col = int(x + 0.5)
                row = int(y + 0.5)
                if row != self._row or col != self._col:
                    if (col >= 0 and col < numcols and
                        row >= 0 and row < numrows):
                        self._col = col
                        self._row = row
                        for data, ax, bkg, art, set_fun in zip(
                                (self._imdata[row, :], self._imdata[:, col]),
                                (self._ax_h, self._ax_v),
                                (self._ax_h_bk, self._ax_v_bk),
                                (self._ln_h, self._ln_v),
                                (self._ln_h.set_ydata, self._ln_v.set_xdata)):
                            self._fig.canvas.restore_region(bkg)
                            set_fun(data)
                            ax.draw_artist(art)
                            self._fig.canvas.blit(ax.bbox)

        def click_cb(event):
            if event.inaxes is not self._im_ax:
                return
            self.active = not self.active
            if self.active:
                self.cur.onmove(event)
                move_cb(event)

        self.move_cid = self._fig.canvas.mpl_connect('motion_notify_event',
                                        move_cb)

        self.click_cid = self._fig.canvas.mpl_connect('button_press_event',
                                        click_cb)

        self.clear_cid = self._fig.canvas.mpl_connect('draw_event', self.clear)
        self._fig.tight_layout()
        self._fig.canvas.draw()

    def clear(self, event):
        self._ax_v_bk = self._fig.canvas.copy_from_bbox(self._ax_v.bbox)
        self._ax_h_bk = self._fig.canvas.copy_from_bbox(self._ax_h.bbox)
        self._ln_h.set_visible(False)
        self._ln_v.set_visible(False)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, val):
        self._active = val
        self.cur.active = val

    def update_cmap(self, cmap):
        self._im.set_cmap(cmap)

    def update_image(self, img_idx):
        self._imdata = self._data_dict[self._key_list[img_idx]]

    def replot(self):
        """
        Update the image displayed by the main axes

        Parameters
        ----------
        new_image : 2D ndarray
           The new image to use
        """
        self.vmin, self.vmax = self._limit_func(self._imdata, self._limit_args)
        # img_dims = new_image.shape
        # set vertical box axes
        self._ax_v.set_xlim(self.vmin, self.vmax)
        # self._ax_v.set_ylim(0, img_dims[1])
        # set horizontal box axes
        self._ax_h.set_ylim(self.vmin, self.vmax)
        # self._ax_h.set_xlim(0, img_dims[0])
        # set main image axes
        # self._im_ax.set_xlim(0, img_dims[0])
        # self._im_ax.set_ylim(0, img_dims[1])
        # if img_dims[0] == img_dims[1]:
        # else:
        #    self._im_ax.set_aspect("auto")
        self._im.set_data(self._imdata)
        self.update_color_limits(self._limit_args, force_update=True)

    def update_norm(self, new_norm):
        """
        Update the way that matplotlib normalizes the image. Default is linear
        """
        self._im.set_norm(new_norm)
        self.update_color_limits(self._limit_args, force_update=True)

    def update_color_limits(self, new_limits, force_update=False):
        """
        Repaint the image when something changes
        """
        # if the limits have to really changed, short-circuit
        if not force_update and self._limit_args == new_limits:
            return
        # assign the new limits
        self._limit_args = new_limits
        # convert limits -> args for clim
        vlim = self._limit_func(self._imdata, self._limit_args)
        # set the color limits
        self._im.set_clim(vlim)
        # set the cross section axes limits
        self._ax_v.set_xlim(*vlim[::-1])
        self._ax_h.set_ylim(*vlim)

    def set_limit_func(self, limit_func, new_limits):
        """
        Set the function to use to determine the color scale

        """
        # set the new function to use for computing the color limits
        self._limit_func = limit_func
        # update the axes
        self.update_color_limits(new_limits, force_update=True)
