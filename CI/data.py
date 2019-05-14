from pathlib import Path
import yaml

import numpy as np

import fitsio


ROOT = Path('/project/projectdirs/desi/spectro/data/')


def swap_cameras(hdus):
    old_map = hdus.hdu_map
    new_map = dict(old_map)
    for old, new in ('ciw', 'cie'), ('cie', 'ciw'), ('cic', 'cin'), ('cin', 'cic'):
        if old in old_map:
            new_map[new] = old_map[old]
            if new not in old_map:
                del new_map[old]
    hdus.hdu_map = new_map
    return hdus


def openCI(night, expid, verbose=True):
    exptag = f'{expid:08d}'
    path = ROOT / str(night) / exptag / f'ci-{exptag}.fits.fz'
    if not path.exists():
        raise RuntimeError(f'File not found: {path}.')
    hdus = fitsio.FITS(str(path))
    # Check for an IMAGECAM header.
    hdr = hdus[1].read_header()
    if 'IMAGECAM' not in hdr:
        hdus.close()
        raise RuntimeError(f'Missing IMAGECAM in {path}.')
    # Check that each listed camera has an HDU present.
    missing = []
    expected = hdr['IMAGECAM'].split(',')
    for camera in expected:
        if camera not in hdus:
            missing.append(camera)
    if missing:
        hdus.close()
        raise RuntimeError(f'Missing HDU for {",".join(missing)} in {path}')
    # Fix CIW,CIE and CIC,CIN swaps before 02-Apr-2019.
    cutoff = 20190402
    if night < cutoff:
        if verbose:
            print(f'Swapping CIW,CIE and CIC,CIN for night {night} < {cutoff}.')
        hdus = swap_cameras(hdus)
    return hdus, hdr


def CIfiles(exposure_table, verbose=False):
    for name in 'id', 'night':
        if name not in exposure_table.columns:
            raise ValueError(f'Table has no "{name}" column.')
    for _, row in exposure_table.iterrows():
        night, expid = row['night'], row['id']
        if night is None or np.isnan(night) or (night < 20190317 or night > 20190701):
            print(f'Invalid night={night}.')
            continue
        # Pandas upcasts int column to float if it contains any invalid values.
        night = int(round(night))
        try:
            hdus, hdr = openCI(night, expid, verbose=verbose)
        except RuntimeError as e:
            print(e)
            continue
        # Check that header has consistent NIGHT and EXPID.
        if hdr['NIGHT'] != night:
            print(f'FITS header ({hdr["NIGHT"]} and db ({night}) have different NIGHT.')
            continue
        if hdr['EXPID'] != expid:
            print(f'FITS header ({hdr["EXPID"]} and db ({expid}) have different EXPID.')
            continue
        try:
            yield hdus, hdr, row
        finally:
            hdus.close()


default_calib = None

def calibrate(hdus, calib=None, steps=1, Tdefault=None):

    global default_calib
    if default_calib is None:
        default_calib = yaml.safe_load(open('calibration.yaml'))
    calib = calib or default_calib

    calibrated = {'HDR': hdus[1].read_header()}
    for camera in ('CIN', 'CIE', 'CIS', 'CIW', 'CIC'):
        if camera in hdus:
            # Always upcast to 32-bit float.
            data = hdus[camera].read().astype(np.float32)
            label, units = 'Raw Data', 'ADU'
            if steps > 0:
                # Subtract bias in ADU
                bias = calib[camera]['bias']
                # This operation upcasts the data from uint16 to float32.
                data -= bias
                label, units = 'Bias Subtracted', 'ADU'
            if steps > 1:
                # Subtract dark current in ADU
                hdr = hdus[camera].read_header()
                T = hdr.get('CCDTEMP', None) or Tdefault
                if T is None:
                    raise ValueError(f'Missing {camera} CCDTEMP and no default: cannot subtract dark current.')
                dark = calib[camera]['D0'] * np.exp(-calib[camera]['T0'] / T)
                data -= dark
                label, units = 'Dark Subtracted', 'ADU'
            if steps > 2:
                # Convert from ADU to elec/s.
                texp = hdr.get('EXPTIME', None)
                if texp is None:
                    raise ValueError(f'Missing {camera} EXPTIME: cannot convert to e/s.')
                if texp <= 0:
                    raise ValueError(f'{camera} EXPTIME = {texp} <= 0.')
                gain = calib[camera]['gain']
                data *= gain / texp
                label, units = 'Gain Corrected', 'elec/s'
            calibrated[camera] = data
    return calibrated, label,  units
