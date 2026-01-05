"""
Utility functions for the Street View dataset tool.
"""

import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image


def num2strdigits(num, digits):
    """
    Convert integer to string with specified number of digits.
    
    Args:
        num: Integer to convert
        digits: Number of digits in output string
        
    Returns:
        String with leading zeros
        
    Example:
        num2strdigits(34, 6) -> '000034'
    """
    str_num = str(num)
    len_str = len(str_num)
    
    if len_str > digits:
        raise ValueError(f'Number of digits ({len_str}) is greater than required ({digits})')
    
    if len_str < digits:
        str_num = '0' * (digits - len_str) + str_num
    
    return str_num


def iminterpnn(iim, U, V):
    """
    Nearest neighbor interpolation for image sampling.
    
    Args:
        iim: Input image (H, W, 3) numpy array
        U: X coordinates to sample (2D array)
        V: Y coordinates to sample (2D array)
        
    Returns:
        Output image (same shape as U/V, 3 channels) as uint8 array
    """
    U = np.round(U).astype(np.int16)
    V = np.round(V).astype(np.int16)
    
    h, w = iim.shape[:2]
    out_h, out_w = U.shape
    
    oim = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    
    # Create valid mask
    valid_mask = (V >= 0) & (V < h) & (U >= 0) & (U < w)
    
    # Sample valid pixels
    valid_v = V[valid_mask]
    valid_u = U[valid_mask]
    
    oim[valid_mask, 0] = iim[valid_v, valid_u, 0]
    oim[valid_mask, 1] = iim[valid_v, valid_u, 1]
    oim[valid_mask, 2] = iim[valid_v, valid_u, 2]
    
    return oim


def bilinear_interp(iim, U, V):
    """
    Bilinear interpolation for image sampling (alternative to nearest neighbor).
    Uses scipy.ndimage.map_coordinates for better quality.
    
    Args:
        iim: Input image (H, W, 3) numpy array
        U: X coordinates to sample (2D array)
        V: Y coordinates to sample (2D array)
        
    Returns:
        Output image (same shape as U/V, 3 channels) as uint8 array
    """
    h, w = iim.shape[:2]
    out_h, out_w = U.shape
    
    oim = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    
    # map_coordinates expects (n_dims, n_points) format
    coordinates = np.array([V.flatten(), U.flatten()])
    
    for c in range(3):
        sampled = map_coordinates(
            iim[:, :, c],
            coordinates,
            order=1,  # bilinear
            mode='constant',
            cval=0,
            prefilter=False
        )
        oim[:, :, c] = sampled.reshape(out_h, out_w).astype(np.uint8)
    
    return oim

