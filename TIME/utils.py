# -*- coding: utf-8 -*-
"""
Created on Sat Jun  4 22:17:13 2022

@author: DELINTE Nicolas
"""

import numpy as np
from dipy.io.streamline import load_tractogram


def tract_to_ROI(trk_file: str):
    '''
    Returns a binary mask of each voxel containing a tractography node. The voxels containing streamlines segments but no nodes will not be selected.

    Parameters
    ----------
    trk_file : str
        Path to tractography file (.trk)

    Returns
    -------
    ROI : 3-D array of shape (x,y,z)
        Binary array containing the ROI associated to the tract in trk_file.

    '''

    trk = load_tractogram(trk_file, 'same')
    trk.to_vox()
    trk.to_corner()

    streams_data = trk.streamlines.get_data()

    b = np.float64(streams_data)
    ROI = np.zeros(trk._dimensions)

    for i in range(b.shape[0]):

        ROI[(int(b[i, 0]), int(b[i, 1]), int(b[i, 2]))] = 1

    return ROI


def peaks_to_RGB(peaksList: list, fracList: list = None, fvfList: list = None):
    '''
    Returns a RGB map of shape (x,y,z,3) representing the main direction of
    of the peaks. Optionnaly scaled by fraction and/or fiber volume fraction.

    Parameters
    ----------
    peaksList : list of 4-D arrays
        List of arrays containing the peaks of shape (x,y,z,3)
    fracList : list of 3-D arrays, optional
        List of arrays of shape (x,y,z) containing the fraction of each fixel.
        The default is None.
    fvfList : list of 3-D arrays, optional
        List of arrays of shape (x,y,z) containing the fiber volume fraction of
        each fixel. The default is None.

    Returns
    -------
    rgb : 4-D array of shape (x,y,z,3)
        RGB map of shape (x,y,z,3) representing the main direction of
        of the peaks.

    '''

    # Safety net
    if type(peaksList) != list:
        if len(peaksList.shape) == 5:
            peaksArray = peaksList.copy()
            peaksList = []
            for k in range(peaksArray.shape[4]):
                peaksList.append(peaksArray[:, :, :, :, k])
        else:
            peaksList = [peaksList]

    K = len(peaksList)

    if fracList is None:
        fracList = []
        for k in range(K):
            fracList.append(np.ones(peaksList[0].shape[:3]))

    if fvfList is None:
        fvfList = []
        for k in range(K):
            fvfList.append(np.ones(peaksList[0].shape[:3]))

    rgb = np.zeros(peaksList[0].shape)

    for xyz in np.ndindex(peaksList[0].shape[:3]):
        for k in range(K):
            rgb[xyz] += abs(peaksList[k][xyz])*fracList[k][xyz]*fvfList[k][xyz]

    return rgb


def tensor_to_DTI(t):
    '''
    Creates fractional anisotropy (FA), axial diffusivity (AD), radial
    diffusivity (RD) and mean diffusivity (MD) maps from a tensor array.

    Parameters
    ----------
    t : 5-D array
        Tensor array of shape (x,y,z,1,6).

    Returns
    -------
    FA : 3-D array
        FA array of shape (x,y,z).
    AD : 3-D array
        AD array of shape (x,y,z).
    RD : 3-D array
        RD array of shape (x,y,z).
    MD : 3-D array
        MD array of shape (x,y,z).

    '''

    np.seterr(divide='ignore', invalid='ignore')

    if len(t.shape) == 4:
        t = t[..., np.newaxis]
        t = np.transpose(t, (1, 2, 3, 4, 0))

        mt = np.array([[t[:, :, :, 0, 0], t[:, :, :, 0, 1], t[:, :, :, 0, 2]],
                      [t[:, :, :, 0, 1], t[:, :, :, 0, 3], t[:, :, :, 0, 4]],
                      [t[:, :, :, 0, 2], t[:, :, :, 0, 4], t[:, :, :, 0, 5]]])

    else:

        mt = np.array([[t[:, :, :, 0, 0], t[:, :, :, 0, 1], t[:, :, :, 0, 3]],
                      [t[:, :, :, 0, 1], t[:, :, :, 0, 2], t[:, :, :, 0, 4]],
                      [t[:, :, :, 0, 3], t[:, :, :, 0, 4], t[:, :, :, 0, 5]]])

    mt = np.transpose(mt, (2, 3, 4, 0, 1))
    val, vec = np.linalg.eig(mt)

    # Sorting to make sure that first dimension contains lambda_max
    val = -np.sort(-val, axis=-1)

    FA = np.sqrt((np.power((val[:, :, :, 0]-val[:, :, :, 1]), 2) +
                  np.power((val[:, :, :, 1]-val[:, :, :, 2]), 2) +
                  np.power((val[:, :, :, 2]-val[:, :, :, 0]), 2))
                 / (2*(np.power(val[:, :, :, 0], 2) +
                       np.power(val[:, :, :, 1], 2) +
                       np.power(val[:, :, :, 2], 2))))

    MD = (val[:, :, :, 0]+val[:, :, :, 1]+val[:, :, :, 2])/3

    AD = val[:, :, :, 0]

    RD = (val[:, :, :, 1]+val[:, :, :, 2])/2

    for m in [FA, MD, RD, AD]:
        m[np.isnan(m)] = 0

    FA = FA.real.astype('float64')
    AD = AD.real.astype('float64')
    RD = RD.real.astype('float64')
    MD = MD.real.astype('float64')

    np.seterr(divide='warn', invalid='warn')

    return FA, AD, RD, MD
