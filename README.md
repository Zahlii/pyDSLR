# pyDSLR - Python Camera Control Made Easy

This library aims at providing an easy to use and fully typed interface to cameras supported by libgphoto2, allowing you to 
capture images and video streams much easier than with native bindings.

The main idea is to have you specify your camera config base class whenever working with the camera, allowing auto-completion of available options as follows:

```python
from pathlib import Path
from pydslr.tools.camera import Camera
from pydslr.config.r6m2 import R6M2Config, ImageSettings, Settings, CaptureSettings

with Camera[R6M2Config]() as c:
    with c.config_context(
        R6M2Config(
            imgsettings=ImageSettings(iso="400"),
            settings=Settings(capturetarget="Internal RAM"),
            capturesettings=CaptureSettings(aperture="5.6", shutterspeed="2"),
        )
    ):
        c.preview_to_file(Path('preview.jpg'))
```

## Adding new camera config types

- Connect your Camera via USB
- Run `python script/create_config.py a7iv --class_name=A7IV` to generate a new file inside app/config named a7iv.py containing the type definitions, with a base class called `A7IVConfig`.
- Open the result file, and rename the classes suffixed with `P_` to something reasonable
- Open a pull request

## Running all checks & tools

```bash
poetry run isort .
poetry run black .
poetry run pylint **/*.py
poetry run mypy . --explicit-package-bases
```