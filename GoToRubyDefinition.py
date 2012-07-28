import sublime, sublime_plugin
import os, fnmatch, re

class DefinitionsIndex:
    def __init__(self):
        self.definitions_index = None

    def index_file(self, filename):
        f = open(filename)
        position = 0
        for line in f:
            match = re.search('(def|class) (\w*)', line)
            if match:
                self.definitions_index.append(Definition(match.group(2), filename, position))
            position += len(line)
        f.close()

    def index_folders(self):
        for directory in sublime.active_window().folders():
            for root, dirs, files in os.walk(directory):
                for basename in files:
                    if fnmatch.fnmatch(basename, "*.rb"):
                        filename = os.path.join(root, basename)
                        self.index_file(filename)

    def build(self):
        self.definitions_index = []
        self.index_folders()
        return self.definitions_index 

    def get(self):
        if self.definitions_index != None:
            return self.definitions_index 
        else:
            self.definitions_index = self.build()
            return self.definitions_index


class Definition:
    def __init__(self, name, filename, position):
        self.name = name
        self.filename = filename
        self.position = position

definitions_index = DefinitionsIndex()


class GoToRubyDefinitionCommand(sublime_plugin.TextCommand):
    def process_selected(self, index):
        if index != -1:
            self.goto_definition(definitions_index.get()[index])

    def run(self, edit):
        self.view.window().show_quick_panel(
            map(lambda x: [x.name, x.filename], definitions_index.get()), 
            self.process_selected
        )

    def goto_definition(self, definition):
        opened_view = self.view.window().open_file(definition.filename)
        opened_view.sel().clear()
        opened_view.sel().add(definition.position)
        opened_view.show(definition.position)

