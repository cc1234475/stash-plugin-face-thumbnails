# Stash plugin: Face Thumbnails

This is a plugin for stash. It adds a `Scan scenes for faces and create thumbnails` task.

It will go through all *NOT* organized scenes that don't have a stashDB id and no URL set and use 
the scrubber thumbnail to find image with a performers face and set it as the thumbnail for the scene.

# How to set it up

Add the python files too your `.stash/plugins` directory

create a `virtualenv`

```bash
virtualenv -p python3 --system-site-packages ~/.stash/plugins/env
source ~/.stash/plugins/env/bin/activate
pip install ~/.stash/plugins/requirements.txt
```

# How to use

Rescan the plugins, you will find a new button in the `Tasks` sections in the settings.
