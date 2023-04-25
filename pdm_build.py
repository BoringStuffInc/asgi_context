from mypyc.build import mypycify


def pdm_build_hook_enabled(context):
    return context.target != "sdist"


def pdm_build_update_setup_kwargs(context, setup_kwargs) -> None:
    setup_kwargs.update(ext_modules=mypycify(["asgi_context/__init__.py"]))
