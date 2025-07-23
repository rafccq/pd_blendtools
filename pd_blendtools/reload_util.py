import importlib
import pkgutil
import pathlib
import os


def reload_modules(modules):
    modules[:] = [importlib.reload(val) for val in modules]

def import_modules(filepath, namespace):
    path = pathlib.Path(filepath).parent.resolve()

    modules = []
    for entry in os.scandir(path):
        if not entry.is_file(): continue
        if not entry.path.endswith('.py'): continue
        if '__init__' in entry.name: continue

        modules.append(entry.name.replace('.py', ''))

    __import__(name=__name__, fromlist=modules)

    modules_loaded = [namespace[name] for name in modules if name in namespace]
    # del namespace

    return modules_loaded

def reload_submodules(path, root=''):
    modulelist = [f'{path}/{root}']
    for modinfo in pkgutil.iter_modules(modulelist):
        if modinfo.name == 'nodes': continue
        # print('----> ', modinfo)
        modname = f'{root}.{modinfo.name}' if root else modinfo.name
        submod = importlib.import_module(modname)
        if modinfo.ispkg:
            print(f'SUBMOD_RELOAD {modinfo.name} (pkg)')
            importlib.reload(submod)
            reload_modules(submod._modules_loaded)
        else:
            importlib.reload(submod)
