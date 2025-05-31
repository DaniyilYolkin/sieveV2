class BasicFilter:
    def __init__(self, result_link_objects: list[dict] = None):
        self.result_link_objects = result_link_objects

    def run(self, link_objects: list[dict]) -> list[dict]:
        self.result_link_objects = link_objects
        return self.result_link_objects
