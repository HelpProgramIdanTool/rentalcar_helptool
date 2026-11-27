"""Keep the two public form plugins on the same input/validation contract."""
from pathlib import Path
import shutil

for plugin in ('prc-bilingual', 'trip-rental-page'):
    for name in ('driver-requirements.js', 'driver-requirements.php'):
        shutil.copyfile(Path('wordpress') / name, Path('wordpress') / plugin / name)
