import sublime, sublime_plugin
import os, fnmatch, re
import threading

class DefinitionsIndex:
    supported_languages = [
        {
            "filematch" : "*.rb",
            "regexp": "(module|def|class) (self\.\w+|\w+)",
            "extract": lambda m: m.group(2)[5:] if m.group(2).startswith("self.") else m.group(2)
        },
        {
            "filematch": "*.py",
            "regexp": "(def|class) (\w+)",
            "extract": lambda m: m.group(2)
        },
        {
            "filematch": "*.scala",
            "regexp": "(trait|object|class|def) (\w+)",
            "extract": lambda m: m.group(2)
        },
        {
            "filematch": "*.js",
            "regexp": "function (\w+)|(\w+): function",
            "extract": lambda m: m.group(1) or m.group(2)
        }
    ]
    
    def __init__(self):
        self.definitions_index = []
        self.status = "uninitialized"

    def index_file(self, filename):
        basename = os.path.basename(filename)
        languages = filter(lambda l: fnmatch.fnmatch(basename, l["filematch"]), DefinitionsIndex.supported_languages)
        if len(languages) == 1:
            language = languages[0]
            f = open(filename)
            position = 0
            for line in f:
                match = re.search(language["regexp"], line)
                if match:
                    name = language["extract"](match)
                    self.definitions_index.append(Definition(name, filename, position))
                position += len(line)
            f.close()

    def reindex_file(self, filename):
        if self.is_initialized():
            self.definitions_index = filter(lambda x: x.filename != filename, self.definitions_index)
            self.index_file(filename)

    def index_folders(self, folders):
        for directory in folders:
            for root, dirs, files in os.walk(directory):
                for basename in files:
                    filename = os.path.join(root, basename)
                    self.index_file(filename)

    def build(self, folders, callback):
        print("Start building index...")
        self.index_folders(folders)
        self.status = "initialized"
        print("Building index finished")
        sublime.set_timeout(lambda: callback(self.definitions_index), 0)

    def is_initialized(self):
        return self.status == "initialized"

    def is_loading(self):
        return self.status == "loading"

    def build_if_needed_and_do(self, callback):
        if self.is_initialized():
            callback(self.definitions_index)
        elif not self.is_loading():
            sublime.status_message("Building index...")
            self.status = "loading"
            thread = threading.Thread(target=self.build,args=(sublime.active_window().folders(), callback, ))
            thread.start()

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

def goto_definition(definition):
    opened_view = sublime.active_window().open_file(definition.filename)
    opened_view.sel().clear()
    opened_view.sel().add(definition.position)
    opened_view.show(definition.position)

class GoToDefinitionDialogCommand(sublime_plugin.WindowCommand):
    def run(self):
        get_definitions_index().build_if_needed_and_do(self.show_panel)

    def show_panel(self, index):
        items = map(lambda x: [x.name, x.filename], index)
        process_selected = lambda i: goto_definition(index[i]) if i != -1 else None
        self.window.show_quick_panel(items, process_selected) 
                        

class GoToDefinitionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        get_definitions_index().build_if_needed_and_do(self.go_to_definition)

    def go_to_definition(self, index):
        word = self.view.substr(self.view.word(self.view.sel()[0]))
        found_definitions = filter(lambda definition: definition.name == word, index)
        if len(found_definitions) == 1:
            goto_definition(found_definitions[0])
        elif len(found_definitions) > 1:
            items = map(lambda x: [x.name, x.filename], found_definitions)
            process_selected = lambda i: goto_definition(found_definitions[i]) if i != -1 else None
            self.view.window().show_quick_panel(items, process_selected)

class IndexUpdater(sublime_plugin.EventListener):
    def on_post_save(self, view):
        get_definitions_index().reindex_file(view.file_name())
