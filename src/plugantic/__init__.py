import dataclasses
from abc import ABC
from typing import Any, get_type_hints
from importlib.metadata import entry_points

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import core_schema

__all__ = [
    "BasePlugin", "PluginLoader",
]


class _PluginConfig(BaseModel):
    """
    An internal class for raw plugin configuration. It is used only to load and instantiate the plugin.
    """

    model_config = ConfigDict(extra="allow")

    name: str
    """
    This field indicated a plugin name, which is a name of the entry point that points to the plugin's class.
    """


class BasePlugin(ABC):
    """
    A base class for plugins. The application should create its own base classes for specific types of plugins, which
    are then inherited by plugin implementations.
    """

    _config: BasePluginConfig
    _config: BaseModel
    """
    A type annotation for configuration model's class for the plugin.
    """

    def __init__(self, config: BasePluginConfig):
        self._config = config


@dataclasses.dataclass(frozen=True)
class PluginLoader:
    """
    A metadata class to annotate a model field as a plugin instance. It takes a `group_name` argument, which is
    a name of the entry points group for plugin lookup.

    Example::

        from typing import Annotated
        from pydantic import BaseModel
        from plugantic import BasePlugin, PluginLoader

        class Config(BaseModel):
            plugin: Annotated[BasePlugin, PluginLoader("app.plugin")]

        c = Config.model_validate({"plugin": {"name": "myplugin"}})

    This tries to load a plugin class from entry point named `myplugin` in `app.plugin` group.

    If plugin doesn't require any configuration parameters to be provided (either doesn't have any or
    provides default values), it is possible to use the shorthand version::

        c = Config.model_validate({"plugin": "myplugin"})

    """

    plugin_group: str
    """A name of an entry point group for annotated plugin"""

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        if not issubclass(source_type, BasePlugin):
            raise RuntimeError(f"{source_type} is not a subclass of {BasePlugin}")

        base_config_class = get_type_hints(source_type)["_config"]

        def validate_from_config(value: str | BasePluginConfig) -> BasePlugin:
            if not isinstance(value, BasePluginConfig):
                value = BasePluginConfig.model_validate({"name": value})
            if not isinstance(value, _PluginConfig):
                value = _PluginConfig.model_validate({"name": value})

            eps = entry_points(name=value.name, group=self.plugin_group)
            try:
                (ep,) = eps
            except ValueError:
                raise ValueError(
                    f"Can't find entry point {value.name} for group {self.plugin_group}"
                )

            try:
                plugin_class = ep.load()
            except Exception as e:
                raise ValueError(
                    f"Can't load entry point {value.name} for group {self.plugin_group}"
                ) from e

            if not issubclass(plugin_class, source_type):
                raise ValueError(f"{plugin_class} is not a subclass of {source_type}")

            plugin_config_class = get_type_hints(plugin_class)["_config"]
            if not issubclass(plugin_config_class, BaseModel):
                raise ValueError(
                    f"{plugin_config_class} is not a subclass of {BaseModel}"
                )

            config = plugin_config_class.model_validate(value.model_extra)

            p = source_type(config)
            return p

        from_plugin_config_schema = core_schema.chain_schema(
            [
                core_schema.union_schema(
                    [
                        core_schema.str_schema(min_length=1),
                        base_config_class.__pydantic_core_schema__,
                    ]
                ),
                core_schema.no_info_plain_validator_function(validate_from_config),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_plugin_config_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(BasePlugin),
                    from_plugin_config_schema,
                ]
            ),
        )
