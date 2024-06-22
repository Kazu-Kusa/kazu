from types import MappingProxyType
from typing import TypeAlias, Callable, Dict, Tuple, Optional, Self

from colorama import Fore
from pyuptech import Color
from terminaltables import SingleTable

from kazu.hardwares import screen

set_all = screen.set_all_leds_same
set_all_single = screen.set_all_leds_single
set_0 = screen.set_led_0
set_1 = screen.set_led_1

ColorSetter: TypeAlias = Callable[[], None]
from kazu.logger import _logger, colorful_int

__black__ = Color.BLACK.value


def set_all_black():
    """
    Set all light to black, used to shut down or init the leds
    """
    set_all(__black__)


class SigLightRegistry(object):
    """
    A registry class for managing signal light purposes associated with color combinations.
    It ensures uniqueness of color-purpose mappings and provides methods to register
    and display these associations.
    """

    def __init__(self, init_registry: Optional[Dict[Tuple[int, int], str]] = None):
        """
        Initializes the signal light registry with an initial mapping.

        Args:
            init_registry (Optional[Dict[Tuple[int, int], str]]):
                A dictionary mapping color pairs to their respective purposes.
        """
        self._registry = init_registry or {}
        self._mapping = MappingProxyType(self._registry)

    @staticmethod
    def make_key(color: Tuple[Color, Color]) -> Tuple[int, int]:
        return color[0].value, color[1].value

    @staticmethod
    def get_key_color_enum(key: Tuple[int, int]) -> Tuple[Color, Color]:
        return Color(key[0]), Color(key[1])

    @staticmethod
    def get_key_color_name(key: Tuple[int, int]) -> Tuple[str, str]:
        return Color(key[0]).name, Color(key[1]).name

    @staticmethod
    def get_key_color_name_colorful(key: Tuple[int, int]) -> Tuple[str, str]:
        return colorful_int(Color(key[0]).name, key[0]), colorful_int(Color(key[1]).name, key[1])

    @staticmethod
    def get_enum_color_name(color: Tuple[Color, Color]) -> Tuple[str, str]:

        return color[0].name, color[1].name

    def _register(self, color: Tuple[Color, Color], purpose: str) -> Self:
        """
        Registers a new color combination with its purpose in the registry.

        Args:
            color (Tuple[Color, Color]): The color combination to register.
            purpose (str): The purpose associated with the color combination.

        Raises:
            ValueError: If the color combination is already registered.

        Returns:
            SigLightRegistry: The current instance for method chaining.
        """
        if color == (Color.BLACK, Color.BLACK):
            raise ValueError(f"All black color is reserved to init the led, you can not register it as signal")
        if (key := self.make_key(color)) in self._registry:
            raise ValueError(
                f"{self.get_enum_color_name(color)} is already registered with the purpose of <{self._registry.get(key)}>! Can not register it with <{purpose}>!"
            )
        if tuple(reversed(key)) in self._registry:
            raise ValueError(
                f"You can't register {(name:=self.get_enum_color_name(color))} with <{purpose}>! Because a mirrored version of {name} is already registered."
            )
        _logger.debug(f"Register SigLight{color} for <{purpose}>" f"\n{self.usage_table}")
        self._registry[key] = purpose
        return self

    def register_all(self, purpose: str, color: Color) -> ColorSetter:
        """
        Registers a color for usage where both lights in a pair display the same color,
        and returns a setter function to apply this setting.

        Args:
            purpose (str): The purpose for setting both lights to the same color.
            color (Color): The color to be set on all lights.

        Returns:
            ColorSetter: A function to set all lights to the specified color.
        """
        self._register((color, color), purpose)
        value = color.value
        func_name = f"set_all_leds_{color.name}"
        source = f"def {func_name}()->None:\n    set_all({value})"

        exec(source, {}, ctx := {"set_all": set_all})
        return ctx.get(func_name)

    def register_singles(self, purpose: str, color_0: Color, color_1: Color) -> ColorSetter:
        """
        Registers a color pair for usage where lights can have different colors within a pair,
        and returns a setter function to apply this setting.

        Args:
            purpose (str): The purpose for the color setting.
            color_0 (Color): The color for the first light.
            color_1 (Color): The color for the second light.

        Returns:
            ColorSetter: A function to set lights to the specified individual color values.
        """
        self._register((color_0, color_1), purpose)
        value_0 = color_0.value
        value_1 = color_1.value
        func_name = f"set_leds_{color_0.name}_{color_1.name}"
        source = f"def {func_name}()->None:\n    set_all_single({value_0}, {value_1})"

        exec(source, {}, ctx := {"set_all_single": set_all_single})
        return ctx.get(func_name)

    @property
    def usage_table(self) -> str:
        """
        Generates a formatted table displaying the current registry of color combinations and their purposes.

        Returns:
            str: A string representation of the registry table.
        """

        trunk = []
        for k, v in self._registry.items():
            name = self.get_key_color_name(k)
            trunk.append((f"{colorful_int(name[0],k[0])}, {colorful_int(name[1],k[1])}", v))

        data = [["Color", "Purpose"]] + trunk

        table = SingleTable(data)
        table.inner_column_border = False
        table.inner_heading_row_border = True
        return f"{Fore.RESET}{table.table}"

    @property
    def mapping(self) -> MappingProxyType[Tuple[int, int], str]:
        """The mapping of the usage registry"""
        return self._mapping

    def clear(self) -> Self:
        """Clear the registry"""

        self._registry.clear()
        return self

    def __enter__(self) -> Self:
        return self.clear()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


sig_light_registry = SigLightRegistry()
