import sublime, sublime_plugin
import os, fnmatch, re
import threading

class DefinitionsIndex:
    def __init__(self):
        self.definitions_index = []
        self.status = "uninitialized"

    def index_file(self, filename):
        f = open(filename)
        position = 0
        for line in f:
            match = re.search('(def|class) (\w*)', line)
            if match:
                self.definitions_index.append(Definition(match.group(2), filename, position))
            position += len(line)
        f.close()

    def index_folders(self, folders):
        for directory in folders:
            for root, dirs, files in os.walk(directory):
                for basename in files:
                    if fnmatch.fnmatch(basename, "*.rb"):
                        filename = os.path.join(root, basename)
                        self.index_file(filename)

    def build(self, folders, on_build_callback):
        print("Start building index...")
        self.index_folders(folders)
        self.status = "initialized"
        print("Building index finished")
        sublime.set_timeout(on_build_callback, 0)

    def start_building(self, on_build_callback):
        sublime.status_message("Building index...")
        if self.status == "uninitialized":
            self.status = "loading"
            thread = threading.Thread(target=self.build,args=(sublime.active_window().folders(), on_build_callback, ))
            thread.start()

    def get(self):
        return self.definitions_index

    def is_initialized(self):
        return self.status == "initialized"

    def is_loading(self):
        return self.status == "loading"


class Definition:
    def __init__(self, name, filename, position):
        self.name = name
        self.filename = filename
        self.position = position

definitions_index_by_window = {}

def get_definitions_index():
    global definitions_index_by_window

    window_id = sublime.active_window().id()
    
    if not window_id in definitions_index_by_window:
        definitions_index_by_window[window_id] = DefinitionsIndex()

    definitions_index = definitions_index_by_window[window_id]
    return definitions_index


class GoToRubyDefinitionCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.show_panel()

    def show_panel(self):
        definitions_index = get_definitions_index()
        if definitions_index.is_initialized():
            self.window.show_quick_panel(
                map(lambda x: [x.name, x.filename], definitions_index.get()), 
                self.process_selected
            )
        elif not definitions_index.is_loading():
            definitions_index.start_building(self.show_panel)
            
    def process_selected(self, index):
        if index != -1:
            self.goto_definition(get_definitions_index().get()[index])

    def goto_definition(self, definition):
        opened_view = self.window.open_file(definition.filename)
        opened_view.sel().clear()
        opened_view.sel().add(definition.position)
        opened_view.show(definition.position)

