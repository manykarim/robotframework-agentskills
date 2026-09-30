"""Dynamic API library (keywords come from get_keyword_names)."""


class DynLib:
    """Dynamic."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def get_keyword_names(self):
        return ["Do Thing"]

    def run_keyword(self, name, args, kwargs=None):
        return name

    def get_keyword_arguments(self, name):
        return ["value"]

    def get_keyword_types(self, name):
        return {"value": int}

    def get_keyword_documentation(self, name):
        return "Do the thing." if name != "__intro__" else "Dynamic library."
