"""
Extract perspective-view cutouts from equirectangular panoramas.

Based on code by Petr Gronat, Michal Havlena, and Jan Knopp,
and edited by Carl Doersch (cdoersch at cs dot cmu dot edu)

More information:
GRONAT, P., HAVLENA , M., SIVIC , J., AND PAJDLA , T. 2011.
Building streetview datasets for place recognition and city reconstruction. 
Tech. Rep. CTU–CMP–2011–16, Czech Tech Univ.
"""

import os
import numpy as np
from scipy.linalg import expm
from PIL import Image
from .utils import iminterpnn, num2strdigits


# Precomputed transformation matrices for common pitch angles
# These are computed once and reused for efficiency
def _compute_pitch_transforms():
    """Precompute transformation matrices for pitch angles -4 and -28 degrees."""
    # Output image parameters
    oimh = 537
    oimw = 936
    hfov = 1.5  # horizontal field of view [rad]
    
    f = oimw / (2 * np.tan(hfov / 2))  # focal length [pix]
    ouc = (oimw + 1) / 2
    ovc = (oimh + 1) / 2
    
    # Create output grid
    X, Y = np.meshgrid(np.arange(1, oimw + 1), np.arange(1, oimh + 1))
    X = X - ouc
    Y = Y - ovc
    Z = f + 0 * X
    
    PTS = np.array([X.flatten(), Y.flatten(), Z.flatten()])
    
    transforms = {}
    
    # Pitch -4 degrees
    pitch = -4
    Tx = expm(np.array([
        [0, 0, 0],
        [0, 0, pitch / 180 * np.pi],
        [0, -pitch / 180 * np.pi, 0]
    ]))
    PTSt = Tx @ PTS
    Xt = PTSt[0, :].reshape(oimh, oimw)
    Yt = PTSt[1, :].reshape(oimh, oimw)
    Zt = PTSt[2, :].reshape(oimh, oimw)
    
    Theta_pitch04 = np.arctan2(Xt, Zt)
    Phi_pitch04 = np.arctan(Yt / np.sqrt(Xt**2 + Zt**2))
    
    transforms[-4] = (Theta_pitch04, Phi_pitch04)
    
    # Pitch -28 degrees
    pitch = -28
    Tx = expm(np.array([
        [0, 0, 0],
        [0, 0, pitch / 180 * np.pi],
        [0, -pitch / 180 * np.pi, 0]
    ]))
    PTSt = Tx @ PTS
    Xt = PTSt[0, :].reshape(oimh, oimw)
    Yt = PTSt[1, :].reshape(oimh, oimw)
    Zt = PTSt[2, :].reshape(oimh, oimw)
    
    Theta_pitch28 = np.arctan2(Xt, Zt)
    Phi_pitch28 = np.arctan(Yt / np.sqrt(Xt**2 + Zt**2))
    
    transforms[-28] = (Theta_pitch28, Phi_pitch28)
    
    return transforms


# Precompute transforms once at module load
_PITCH_TRANSFORMS = _compute_pitch_transforms()


def extract_cutout(panorama, yaw, pitch, use_bilinear=False):
    """
    Extract a single perspective-view cutout from an equirectangular panorama.
    
    Args:
        panorama: Input panorama image (H, W, 3) as numpy array
        yaw: Horizontal angle in degrees (0-360)
        pitch: Vertical angle in degrees (typically -4 or -28)
        use_bilinear: Use bilinear interpolation instead of nearest neighbor
        
    Returns:
        Cutout image (537, 936, 3) as uint8 numpy array
    """
    # Input/output image parameters
    iimh = 3328
    iimw = 6656
    oimh = 537
    oimw = 936
    
    sw = iimw / (2 * np.pi)
    sh = iimh / np.pi
    iuc = (iimw + 1) / 2
    ivc = (iimh + 1) / 2
    
    # Get precomputed transform for this pitch, or compute on the fly
    if pitch in _PITCH_TRANSFORMS:
        THETA, PHI = _PITCH_TRANSFORMS[pitch]
    else:
        # Compute transform for arbitrary pitch (slower)
        hfov = 1.5
        f = oimw / (2 * np.tan(hfov / 2))
        ouc = (oimw + 1) / 2
        ovc = (oimh + 1) / 2
        
        X, Y = np.meshgrid(np.arange(1, oimw + 1), np.arange(1, oimh + 1))
        X = X - ouc
        Y = Y - ovc
        Z = f + 0 * X
        
        PTS = np.array([X.flatten(), Y.flatten(), Z.flatten()])
        Tx = expm(np.array([
            [0, 0, 0],
            [0, 0, np.radians(pitch)],
            [0, -np.radians(pitch), 0]
        ]))
        PTSt = Tx @ PTS
        Xt = PTSt[0, :].reshape(oimh, oimw)
        Yt = PTSt[1, :].reshape(oimh, oimw)
        Zt = PTSt[2, :].reshape(oimh, oimw)
        
        THETA = np.arctan2(Xt, Zt)
        PHI = np.arctan(Yt / np.sqrt(Xt**2 + Zt**2))
    
    # Apply yaw rotation
    yaw_rad = np.radians(yaw)
    THETA = THETA + yaw_rad
    
    # Wrap around (handle boundaries)
    idx = THETA < np.pi
    THETA[idx] = THETA[idx] + 2 * np.pi
    idx = THETA >= np.pi
    THETA[idx] = THETA[idx] - 2 * np.pi
    
    # Map to panorama coordinates
    U = sw * THETA + iuc
    V = sh * PHI + ivc
    
    # Sample from panorama
    if use_bilinear:
        from .utils import bilinear_interp
        oim = bilinear_interp(panorama, U, V)
    else:
        oim = iminterpnn(panorama, U, V)
    
    return oim


def extract_cutouts_from_panorama(panorama, pano_idx, mappings, cutout_folder, digits=6):
    """
    Extract multiple cutouts from a panorama based on mapping data.
    
    Args:
        panorama: Panorama image array (H, W, 3)
        pano_idx: Panorama index
        mappings: List of dicts with keys: 'yawRel', 'pitch', 'fname', 'savedir'
        cutout_folder: Base folder for cutouts
        digits: Number of digits for panorama filename
        
    Returns:
        Number of cutouts successfully extracted
    """
    os.makedirs(cutout_folder, exist_ok=True)
    
    # Filter mappings for this panorama
    pano_mappings = [m for m in mappings if m['Idx'] == pano_idx]
    
    if not pano_mappings:
        return 0
    
    # Check if already processed
    first_mapping = pano_mappings[0]
    cutout_path_city = os.path.join(cutout_folder, first_mapping['savedir'])
    first_file = os.path.join(cutout_path_city, first_mapping['fname'])
    
    if os.path.exists(first_file):
        print(f"Skipping panorama {pano_idx} (already processed)")
        return len(pano_mappings)
    
    extracted = 0
    
    # Process each cutout
    for mapping in pano_mappings:
        cutout_path_city = os.path.join(cutout_folder, mapping['savedir'])
        cutout_file = os.path.join(cutout_path_city, mapping['fname'])
        
        # Skip if already exists
        if os.path.exists(cutout_file):
            continue
        
        # Extract cutout
        yaw = mapping['yawRel']
        pitch = mapping['pitch']
        
        cutout = extract_cutout(panorama, yaw, pitch)
        
        # Save cutout
        os.makedirs(cutout_path_city, exist_ok=True)
        Image.fromarray(cutout).save(cutout_file, 'JPEG')
        
        print(f"Saved cutout: {cutout_file}")
        extracted += 1
    
    return extracted

