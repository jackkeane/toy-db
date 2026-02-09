from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "toydb._storage_engine",
        sources=[
            "cpp/bindings/python_bindings.cpp",
            "cpp/src/page.cpp",
            "cpp/src/page_manager.cpp",
            "cpp/src/buffer_pool.cpp",
            "cpp/src/btree.cpp",
            "cpp/src/wal.cpp",
        ],
        include_dirs=["cpp/include"],
        cxx_std=17,
    ),
]

setup(
    cmdclass={"build_ext": build_ext},
    ext_modules=ext_modules,
)
