from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class NoDocs:
    @keyword
    def undocumented(self, value: int) -> int:
        return value
