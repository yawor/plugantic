# plugantic

A [pydantic](https://github.com/pydantic/pydantic) based plugin loading and configuration.

This library provides classes, which can be used in pydantic based application configuration to load and configure
plugin instances, which are then available directly from the configuration model instance.

The library uses python's entry points to define available plugins.

The `BasePlugin` class provided in the library doesn't provide any implementation specific to how the application should
use the plugins. It only implements a mechanisms for lookup, loading and configuring the plugins' instances.
It's up to the application itself to implement application-specific interfaces.

## Example

This code defines base plugin (`BaseApplicationPlugin`) and plugin config model (`BaseApplicationPluginConfig`) classes
specific for the application. The `BaseApplicationPlugin` defines that it uses `BaseApplicationPluginConfig` as its
config model. Any plugin implementation that inherits from `BaseApplicationPlugin` must use a config model which is
either `BaseApplicationPluginConfig` or inherits from it. It is checked in the runtime, and validation errors are raised
if this is not true.

It also defines an application config model class, which has `plugins` field, which holds a list of plugin instances.
The plugins are going to be looked up in `myapp.plugin` entry point group. The config model expects that all plugins
in this field have to inherit from `BaseApplicationPlugin`.

```python
from abc import ABC
from typing import Annotated

from yaml import safe_load
from pydantic import BaseModel
from plugantic import PluginAnnotation, BasePlugin, BasePluginConfig


class BaseApplicationPluginConfig(BasePluginConfig):
    x: int = 0


class BaseApplicationPlugin(BasePlugin, ABC):
    _config: BaseApplicationPluginConfig

    def application_specific_method(self):
        ...


class ApplicationConfig(BaseModel):
    plugins: list[Annotated[BaseApplicationPlugin, PluginAnnotation("myapp.plugin")]]


def main():
    with open("config.yaml") as config_file:
        config = ApplicationConfig.model_validate(safe_load(config_file))

    print(config.plugins)
```

An example configuration file for the above code could look like this:

```yaml
plugins:
  - name: cool_plugin
    x: 10
  - other_plugin
```

It defines two plugins:

- The first one is named `cool_plugin`. It also sets the `x` parameter in the plugin's config
  to 10.
- The second one is named `other_plugin` and it uses a shorthand configuration form, where only a name is provided
  instead a full dictionary with a `name` key. It is possible to use shorthand form only if the plugin doesn't
  take any configuration parameters or if default values are provided in the plugin's config model like in the example
  above.

This is equivalent to:

```yaml
plugins:
  - name: cool_plugin
    x: 10
  - name: other_plugin
```

The plugins themselves must be provided by registering entry points for requested entry point groups. An example
definition of a plugin in `pyproject.toml` in a package providing the plugins may look like this:

```toml
[project.entry-points."myapp.plugin"]
cool_plugin = "myapp_plugins.cool_pluging:CoolPlugin"
other_plugin = "myapp_plugins.other_plugin:OtherPlugin"
```

The entry point needs to point to a class which inherits from the `PluginAnnotation` annotated class in the config
model.
