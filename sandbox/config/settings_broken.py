# Deliberately broken: imports a module that does not exist (tests the error screen).
import this_module_does_not_exist  # noqa: F401

from config.settings import *
