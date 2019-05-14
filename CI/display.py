import datetime

import numpy as np
import numpy.lib.stride_tricks

import scipy.stats

import matplotlib
matplotlib.use('AGG')
import matplotlib.pyplot as plt


def block_view(A, block_shape):
    """Provide a 2D block view of a 2D array.
    Returns a view with shape (n, m, a, b) for an input 2D array with
    shape (n*a, m*b) and block_shape of (a, b).
    """
    assert len(A.shape) == 2, '2D input array is required.'
    assert A.shape[0] % block_shape[0] == 0, \
        'Block shape[0] does not evenly divide array shape[0].'
    assert A.shape[1] % block_shape[1] == 0, \
        'Block shape[1] does not evenly divide array shape[1].'
    shape = (A.shape[0] // block_shape[0], A.shape[1] // block_shape[1]) + block_shape
    strides = (block_shape[0] * A.strides[0], block_shape[1] * A.strides[1]) + A.strides
    return numpy.lib.stride_tricks.as_strided(A, shape=shape, strides=strides)


def downsample(data, downsampling, summary=np.median):
    return summary(block_view(data, (downsampling, downsampling)), axis=(2, 3))


def thumbnail(data, label, units, downsampling=16, summary=np.median, vmin='0.5%', vmax='99.5%',
              nbins=50, localoffsets=True, meta=True, cmap='magma_r', save=None):
    cameras = 'CIN', 'CIE', 'CIS', 'CIW', 'CIC'
    
    # vmin, vmax can be percentiles as strings, e.g., '1%', '99%'.
    pmin = float(vmin[:-1]) if str(vmin)[-1] == '%' else None
    pmax = float(vmax[:-1]) if str(vmax)[-1] == '%' else None

    # Subtract local clipped median offsets, if requested.
    if localoffsets:
        offset = {}
        for camera in cameras:
            if camera not in data:
                continue
            clipped, _, _ = scipy.stats.sigmaclip(data[camera])
            offset[camera] = np.mean(clipped)
            print(camera,  'offset', offset[camera], units)
    else:
        offset = {camera: 0. for camera in cameras}
        
    # Downsample each camera image.
    downsampled = {}
    for camera in cameras:
        if camera not in data:
            continue
        downsampled[camera] = downsample(data[camera] - offset[camera], downsampling, summary)
        
    # Calculate percentile limits if necessary.
    if pmin is not None or pmax is not None:
        all_downsampled = np.concatenate([D.reshape(-1) for D in downsampled.values()])
        if pmin is not None:
            vmin = np.percentile(all_downsampled, pmin)
        if pmax is not None:
            vmax = np.percentile(all_downsampled, pmax)
    if vmin >= vmax:
        raise ValueError('Expected vmin < vmax.')

    # Initialize figure.
    fig = plt.figure(figsize=(12, 12))
    ax = fig.add_axes([0., 0., 1., 1.])
    ax.axis('off')
    if nbins:
        xpad, ybtm = 0.001, 0.03
        hax = fig.add_axes([xpad, ybtm, 2./7. - 2 * xpad, 2./7. - ybtm])
        bins = np.linspace(vmin, vmax, nbins + 1)
        hax.set_xlim(bins[0], bins[-1])
        hax.set_yscale('log')
        hax.tick_params(direction='in', which='both')
        hax.set_xticklabels([])
        hax.set_yticklabels([])
        #hax.spines['top'].set_visible(False)
        #hax.spines['right'].set_visible(False)
        # Draw a colorbar below the histogram.
        v = np.linspace(vmin, vmax, 200).reshape(1, -1)
        vax = fig.add_axes([xpad,  0., 2./7. - 2 * xpad, ybtm])
        vax.axis('off')
        vax.imshow(v, aspect='auto', cmap=cmap)

    # Apply pixel value stretch.
    #stretch = astropy.visualization.HistEqStretch(np.stack([D.reshape(-1) for D in downsampled.values()]))

    # Draw thumbnails. The (x,y) flips below are based on DESI-3347 and have
    # also been checked against SDSS stars in the legacy viewer.
    ny, nx = 2048 // downsampling, 3072 // downsampling
    img = np.full((nx + 2 * ny, nx + 2 * ny), np.nan)
    for camera in cameras:
        if camera not in data:
            continue
        if nbins:
            hax.hist(downsampled[camera].reshape(-1), bins=bins, histtype='step', label=camera)
        if camera == 'CIS':
            img[0:ny,ny:ny+nx] = downsampled[camera]
        elif camera == 'CIE':
            img[ny:ny+nx,0:ny] = downsampled[camera][:, ::-1].T
        elif camera == 'CIN':
            img[ny+nx:2*ny+nx,ny:ny+nx] = downsampled[camera][::-1,::-1]
        elif camera == 'CIW':
            img[ny:ny+nx,ny+nx:2*ny+nx] = downsampled[camera][::-1].T
        elif camera == 'CIC':
            n = ny + (nx - ny) // 2
            img[n:n+ny,ny:ny+nx] = downsampled[camera][::-1,::-1]
    ax.imshow(img, origin='lower', interpolation='none', vmin=vmin, vmax=vmax, cmap=cmap)

    # Add metadata text.
    if meta:
        hdr = data.get('HDR', None)
        RA, DEC = hdr['SKYRA'], hdr['SKYDEC']
        url = f'http://legacysurvey.org/viewer-dev?ra={RA}&dec={DEC}&zoom=8&layer=sdss2&desifoot={RA},{DEC}'
        print(url)
        night, MJD = hdr['NIGHT'], hdr['MJD-OBS']
        # Calculate local noon on the night of this observation.
        #noon = datetime.datetime.strptime(str(night), '%Y%m%d').replace(hour=7)
        # Convert MJD to local time.
        local = datetime.datetime(1858, 11, 17) + datetime.timedelta(days=MJD, hours=-7)
        localtime = local.time().strftime('%H:%M:%S')
        y, dy = 1., 0.025
        line = f"#{hdr['EXPID']} {night} {localtime}+{hdr['EXPTIME']:.0f}s"
        ax.text(0., y, line, verticalalignment='top', transform=ax.transAxes, fontsize=13)
        y -= dy
        line = f"{hdr['FLAVOR'].strip()}:{hdr['PROGRAM'].strip()[:25]}"
        ax.text(0., y, line, verticalalignment='top', transform=ax.transAxes, fontsize=13)
        y -= dy
        line = f"RA {RA:9.5f} DEC {DEC:9.5f}"
        ax.text(0., y, line, verticalalignment='top', transform=ax.transAxes, fontsize=13)
        y -= dy
        line = f"HA {hdr['MOUNTHA']:6.2f} EL {hdr['MOUNTEL']:5.1f} AZ {hdr['MOUNTAZ']:5.1f}"
        ax.text(0., y, line, verticalalignment='top', transform=ax.transAxes, fontsize=13)
        y -= dy

    if save is not None:
        plt.savefig(save)
        plt.close(fig)
