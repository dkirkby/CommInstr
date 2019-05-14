import sys
import os
import yaml
from pathlib import Path

import CI.db
import CI.data
import CI.display


def main(*args):
    # Lookup the science exposures for this night.
    night = int(sys.argv[1])
    db = CI.db.DB()
    exposures = db.select(
        'exposure.exposure', 'id,night',
        where= f"sequence='CI' and flavor='science' and night={night}", limit=None, order='id')
    # Initialize the output path.
    OUT = Path(os.getenv('SCRATCH')) / 'CI' / str(night)
    OUT.mkdir(parents=True, exist_ok=True)
    # Loop over exposures.
    meta = []
    for hdus, hdr, row in CI.data.CIfiles(exposures, verbose=True):
        tag = f"{row['id']:08d}"
        save = str(OUT / (tag + '.jpg'))
        try:
            CI.display.thumbnail(*CI.data.calibrate(hdus), nbins=0, save=save)
            meta.append(dict(EXPID=tag, RA=hdr['SKYRA'], DEC=hdr['SKYDEC']))
        except Exception as e:
            print(f'Failed for EXPID {expid}: {e}')
            raise e
    # Save the night metadata.
    with open(OUT / f'{night}.yaml', 'w') as f:
        yaml.dump(meta, f)


if __name__ == '__main__':
    main()
