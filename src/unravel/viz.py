# -*- coding: utf-8 -*-
"""
Created on Sat Apr  8 20:41:36 2023

@author: DELINTE Nicolas
"""

import numpy as np
from tqdm import tqdm
from PIL import Image
from scipy.ndimage import zoom
import pyvista
import matplotlib.pyplot as plt
from matplotlib import cm
from unravel.core import (angular_weighting,  relative_angular_weighting,
                          closest_fixel_only)


def grayscale_to_rgb(array):
    '''
    Reapeats a 3D array three times to create a 3D rgb image.

    Parameters
    ----------
    array : 3-D array of shape (x,y,z)
        Grayscale array.

    Returns
    -------
    array : 3-D array of shape (x,y,z,3)
        grayscale (rgb) image.

    '''

    array = np.repeat(array[..., np.newaxis], 3, axis=3)

    return array


def overlap_volumes(vol_list: list, rgb: bool = True, order: int = 0):
    '''
    Overlaps multiple volumes, zero is taken as transparent.
    Order of list is important : [foreground,...,background]

    Parameters
    ----------
    vol_list : list
        List of 3-D array of shape (x,y,z) or (x,y,z,3).
    rgb : bool, optional
        Output rgb volume. The default is True.
    order : int, optional
        Increases quality when increasing resolution, also increases computation
        time. The default is 0.


    Returns
    -------
    back : 3-D array of shape (x,y,z) or (x,y,z,3).
        Overlaped volumes.

    '''

    max_size = [0, 0, 0]

    for vol in vol_list:
        x, y, z = vol.shape[:3]
        for axis, i in enumerate([x, y, z]):
            if i > max_size[axis]:
                max_size[axis] = i

    back = np.zeros(tuple(max_size)+(3,))

    while len(vol_list) > 0:

        layer = vol_list.pop()
        if layer.shape[-1] != 3:
            layer = grayscale_to_rgb(layer)

        size = list(layer.shape[:3])

        layer = zoom(layer, tuple([i / j for i, j in zip(max_size, size)])+(1,),
                     order=order)

        # Normalize
        layer /= np.max(layer)

        back[np.sum(layer, axis=3) != 0] = layer[np.sum(layer, axis=3) != 0]

    if rgb:

        return back

    else:

        return back[:, :, :, 0]


def convert_to_gif(array, output_folder: str, extension: str = 'webp',
                   axis: int = 2, transparency: bool = False,
                   keep_frames: bool = False):
    '''
    Creates a GIF from a 3D volume.

    Parameters
    ----------
    array : 3-D array of shape (x,y,z) or (x,y,z,3)
        DESCRIPTION.
    output_folder : str
        Output filename. Ex: 'output_path/filename'
    extension : str, optional
        File format. The default is 'webp'.
    axis : int, optional
        Axis number to iterate over. The default is 2.
    transparency : bool, optional
        If True, zero is converted to transparent. The default is False.
    keep_frames : bool, optional
        Only if transparent and gif. Overlaps new frames onto old frames.
        The default is False.

    Returns
    -------
    None.

    '''

    frames = []

    # Normalize
    array /= np.max(array)

    if len(array.shape) == 3:       # If not RGB
        array = grayscale_to_rgb(array)

    for i in tqdm(range(array.shape[axis])):

        slic = tuple([i if d == axis else slice(None)
                      for d in range(len(array.shape))])

        data = array[slic]

        if transparency:
            alpha = (np.sum(data, axis=2) != 0)*1
            data = np.dstack((data, alpha))

        data = (data*255).astype('uint8')

        image = Image.fromarray(data)
        frames.append(image)

    if keep_frames:
        disposal = 0
    else:
        disposal = 2

    frames[0].save(output_folder+'.'+extension,
                   lossless=True, save_all=True, append_images=frames,
                   disposal=disposal)


def compute_alpha_surface(vList: list, method: str = 'raw'):
    '''
    Computes the mesh for the alpha coefficient surface based on the vectors of
    vList.

    Parameters
    ----------
    vList : list
        List of the k vectors corresponding to each fiber population
    method : str, optional
        Method used for the relative contribution, either;
            'ang' : angular weighting
            'raw' : relative angular weighting
            'cfo' : closest-fixel-only
            'vol' : relative volume weighting.
        The default is 'raw'.

    Returns
    -------
    x : array of float64 of size (200,200)
        Mesh X coordinates.
    y : array of float64 of size (200,200)
        Mesh Y coordinates.
    z : array of float64 of size (200,200)
        Mesh Z coordinates.
    coef : array of float64 of size (200,200)
        Alpha coefficients.

    '''

    nList = [0]*len(vList)

    u = np.linspace(0, 2 * np.pi, 200)
    v = np.linspace(0, np.pi, 200)

    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones(np.size(u)), np.cos(v))

    coef = x.copy()

    for xyz in np.ndindex(x.shape):

        if method == 'raw':
            a = relative_angular_weighting([x[xyz], y[xyz], z[xyz]],
                                           vList, nList)[0]
        elif method == 'cfo':
            a = closest_fixel_only([x[xyz], y[xyz], z[xyz]], vList, nList)[0]
        else:
            a = angular_weighting([x[xyz], y[xyz], z[xyz]], vList, nList)[0]

        x[xyz] *= (a+1)
        y[xyz] *= (a+1)
        z[xyz] *= (a+1)
        coef[xyz] = a

    return x, y, z, coef


def plot_alpha_surface_matplotlib(vList: list, method: str = 'raw',
                                  show_v: bool = False):
    '''
    Computes and plots the mesh for the alpha coefficient surface based on the
    vectors of vList.

    Parameters
    ----------
    vList : list
        List of the k vectors corresponding to each fiber population
    method : str, optional
        Method used for the relative contribution, either;
            'ang' : angular weighting
            'raw' : relative angular weighting
            'cfo' : closest-fixel-only
            'vol' : relative volume weighting.
        The default is 'raw'.
    show_v : bool, optional
        Show vectors. The default is False.

    Returns
    -------
    None.

    '''

    x, y, z, coef = compute_alpha_surface(vList, method=method)

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.plot_surface(x, y, z, facecolors=cm.plasma(coef), rstride=1, cstride=1)
    if show_v:
        for j, v in enumerate(vList):
            v = v/np.linalg.norm(v)*2.5
            if j == 0:
                ax.plot([-v[0], v[0]], [-v[1], v[1]], zs=[-v[2], v[2]],
                        color='orange')
            else:
                ax.plot([-v[0], v[0]], [-v[1], v[1]], zs=[-v[2], v[2]],
                        color='white')
    ax.set_aspect('equal')

    plt.show()


def plot_alpha_surface_pyvista(vList: list, method: str = 'raw',
                               show_v: bool = False):
    '''
    Computes and plots the mesh for the alpha coefficient surface based on the
    vectors of vList.

    Parameters
    ----------
    vList : list
        List of the k vectors corresponding to each fiber population
    method : str, optional
        Method used for the relative contribution, either;
            'ang' : angular weighting
            'raw' : relative angular weighting
            'cfo' : closest-fixel-only
            'vol' : relative volume weighting.
        The default is 'raw'.
    show_v : bool, optional
        Show vectors. The default is False.

    Returns
    -------
    None.

    '''

    x, y, z, coef = compute_alpha_surface(vList, method=method)

    pc = pyvista.StructuredGrid(x, y, z)
    pl = pyvista.Plotter()
    _ = pl.add_mesh(pc, cmap='plasma', scalars=coef.T.flatten(),
                    smooth_shading=True, show_scalar_bar=False)
    if show_v:
        points = []
        for j, v in enumerate(vList):
            v = v/np.linalg.norm(v)*2.5
            points.append([i*-1 for i in v])
            points.append(v)
            if j == 0:
                _ = pl.add_lines(np.array(points), label=str(v), color='orange')
            else:
                _ = pl.add_lines(np.array(points), label=str(v), color='white')
            points = []
        pl.add_legend()
    pl.show()


def export_alpha_surface(vList: list, output_path: str, method: str = 'raw',
                         show_v: bool = True):
    '''
    Computes and exports the mesh for the alpha coefficient surface based on the
    vectors of vList.

    Tutorial to powerpoint: save as .gltf, open with 3D viewer, save as .glb,
    open with 3D builder then repair then save as .3mf

    Parameters
    ----------
    vList : list
        List of the k vectors corresponding to each fiber population
    output_path : str
        Output filename.
    method : str, optional
        Method used for the relative contribution, either;
            'ang' : angular weighting
            'raw' : relative angular weighting
            'cfo' : closest-fixel-only
            'vol' : relative volume weighting.
        The default is 'raw'.
    show_v : bool, optional
        Show vectors. The default is True.

    Returns
    -------
    None.

    '''

    x, y, z, coef = compute_alpha_surface(vList, method=method)

    pc = pyvista.StructuredGrid(x, y, z)
    pl = pyvista.Plotter()
    _ = pl.add_mesh(pc, cmap='plasma', scalars=coef.T.flatten(),
                    smooth_shading=True, show_scalar_bar=False)
    if show_v:
        points = []
        for j, v in enumerate(vList):
            v = v/np.linalg.norm(v)*2.5
            points.append([i*-1 for i in v])
            points.append(v)
            if j == 0:
                _ = pl.add_lines(np.array(points), label=str(v), color='orange')
            else:
                _ = pl.add_lines(np.array(points), label=str(v), color='white')
            points = []
    pl.export_gltf(output_path)