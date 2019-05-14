import os
from pathlib import Path
import yaml
import json


def main():
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
    with open('merged.json', 'w') as f:
        json.dump(merged, f, indent=2)
    print(f'Merged {nexptot} exposures.')

if __name__ == '__main__':
    main()

