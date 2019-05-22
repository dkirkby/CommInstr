import sys
import os
from pathlib import Path
import yaml
import json


def main():
    if len(sys.argv) == 2:
        only_night = int(sys.argv[1])
        only_night = f'{only_night:08d}'
    else:
        only_night = None
    ROOT = Path(os.getenv('SCRATCH')) / 'CI'
    assert ROOT.exists()
    merged = {}
    nexptot = 0
    for path in ROOT.glob('2019????'):
        night = str(path)[-8:]
        config_path = path / (night + '.yaml')
        if not config_path.exists():
            print(f'Skipping {night} with no config.')
            continue
        with open(config_path) as f:
            exposures = yaml.safe_load(f)
            print(f'Merged {len(exposures)} exposures for {night}.')
            merged[night] = exposures
            nexptot += len(exposures)
    outname = 'merged.js'
    with open(outname, 'w') as f:
        print('initnights(', file=f)
        json.dump(merged, f, indent=2)
        print(');', file=f)
    print(f'Merged {nexptot} exposures into {outname}.')
    if only_night:
        print(f'mkdir $DESI_WWW/users/dkirkby/CI/{only_night}')
        print(f'cp $SCRATCH/CI/{only_night}/*.jpg $DESI_WWW/users/dkirkby/CI/{only_night}/')
    print(f'mv {outname} docs/js/')
    print(f'git add docs/js/{outname}')
    print(f'git commit -m "Add {only_night}"')
    print(f'git push')


if __name__ == '__main__':
    main()

