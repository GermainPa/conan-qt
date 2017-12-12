import os
from distutils.spawn import find_executable
from conans import ConanFile, tools, VisualStudioBuildEnvironment
from conans.tools import cpu_count


def which(program):
    """
    Locate a command.
    """
    def is_exe(fpath):
        """
        Check if a path is executable.
        """
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

class QtConan(ConanFile):
    """
    Qt Conan package
    """
    name = "Qt"
    version = "5.9.2"
    description = "Conan.io package for Qt library."
    source_dir = "qt5"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "opengl": ["desktop", "dynamic"],
        "canvas3d": [True, False],
        "gamepad": [True, False],
        "graphicaleffects": [True, False],
        "imageformats": [True, False],
        "location": [True, False],
        "serialport": [True, False],
        "svg": [True, False],
        "tools": [True, False],
        "webengine": [True, False],
        "websockets": [True, False],
        "xmlpatterns": [True, False],
        "openssl": ["no", "yes", "linked"]
    }
    default_options = "opengl=dynamic", "canvas3d=False", "gamepad=False", "graphicaleffects=False", "imageformats=False", "location=False", "serialport=False", "svg=False", "tools=False", "webengine=False", "websockets=False", "xmlpatterns=False", "openssl=no"
    url = "https://github.com/ArobasMusic/conan-qt"
    license = "http://doc.qt.io/qt-5/lgpl.html"
    short_paths = True

    def config_options(self):
        if self.settings.os != "Windows":
            del self.options.opengl
            del self.options.openssl

    def requirements(self):
        if self.settings.os == "Windows":
            if self.options.openssl == "yes":
                self.requires("OpenSSL/1.0.2l@conan/stable", dev=True)
            elif self.options.openssl == "linked":
                self.requires("OpenSSL/1.0.2l@conan/stable")

    def source(self):
        submodules = ["qtbase"]

        if self.options.canvas3d:
            submodules.append("qtcanvas3d")
        if self.options.gamepad:
            submodules.append("qtgamepad")
        if self.options.graphicaleffects:
            submodules.append("qtgraphicaleffects")
        if self.options.imageformats:
            submodules.append("qtimageformats")
        if self.options.location:
            submodules.append("qtlocation")
        if self.options.serialport:
            submodules.append("qtserialport")
        if self.options.svg:
            submodules.append("qtsvg")
        if self.options.tools:
            submodules.append("qttools")
        if self.options.webengine:
            submodules.append("qtwebengine")
        if self.options.websockets:
            submodules.append("qtwebsockets")
        if self.options.xmlpatterns:
            submodules.append("qtxmlpatterns")

        self.run("git clone https://code.qt.io/qt/qt5.git")
        self.run("cd {} && git checkout v{}".format(self.source_dir, self.version))
        self.run("cd {} && perl init-repository --no-update --module-subset={}".format(self.source_dir, ",".join(submodules)))
        self.run("cd {} && git submodule update".format(self.source_dir))

        if self.settings.os != "Windows":
            self.run("chmod +x ./{}/configure".format(self.source_dir))

    def build(self):
        """ Define your project building. You decide the way of building it to
            reuse it later in any other project.
        """
        args = [
            "-opensource",
            "-confirm-license",
            "-nomake examples",
            "-nomake tests",
            "-prefix {}".format(self.package_folder)
        ]
        if not self.options.shared:
            args.insert(0, "-static")
        if self.settings.build_type == "Debug":
            args.append("-debug")
        else:
            args.append("-release")

        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            self._build_msvc(args)
        else:
            self._build_unix(args)

    def _build_msvc(self, args):
        build_command = find_executable("jom.exe")
        if build_command:
            build_args = ["-j", str(cpu_count())]
        else:
            build_command = "nmake.exe"
            build_args = []
        self.output.info("Using '{} {}' to build".format(build_command, " ".join(build_args)))

        env = {}
        env.update({'PATH': [
            "C:\\Perl64\\bin",
            "C:\\Program Files (x86)\\Windows Kits\\8.1\\bin\\x86",
            "{}\\qtbase\\bin".format(self.conanfile_directory),
            "{}\\gnuwin32\\bin".format(self.conanfile_directory),
            "{}\\qtrepotools\\bin".format(self.conanfile_directory)
        ]})

        # it seems not enough to set the vcvars for older versions
        if self.settings.compiler == "Visual Studio":
            if self.settings.compiler.version == "14":
                args += ["-platform win32-msvc2015"]
            if self.settings.compiler.version == "12":
                args += ["-platform win32-msvc2013"]
            if self.settings.compiler.version == "11":
                args += ["-platform win32-msvc2012"]
            if self.settings.compiler.version == "10":
                args += ["-platform win32-msvc2010"]

        args += ["-opengl {}".format(self.options.opengl)]
        if self.options.opengl == "dynamic":
            args += ["-angle"]
            env.update({'QT_ANGLE_PLATFORM': 'd3d11'})

        if self.options.openssl == "no":
            args += ["-no-openssl"]
        elif self.options.openssl == "yes":
            args += ["-openssl"]
        else:
            args += ["-openssl-linked"]

        env_build = VisualStudioBuildEnvironment(self)
        env.update(env_build.vars)

        with tools.environment_append(env):
            vcvars = tools.vcvars_command(self.settings)
            self.run("cd {} && {} && set".format(self.source_dir, vcvars))
            self.run("cd {} && {} && configure {}".format(self.source_dir, vcvars, " ".join(args)))
            self.run("cd {} && {} && {} {}".format(self.source_dir, vcvars, build_command, " ".join(build_args)))
            self.run("cd {} && {} && {} install".format(self.source_dir, vcvars, build_command))

    def _build_unix(self, args):
        args += ["-silent", "-no-framework"]
        if self.settings.arch == "x86":
            args += ["-platform macx-clang-32"]
        self.output.info("Using '{}' threads".format(cpu_count()))
        self.run("cd {} && ./configure {}".format(self.source_dir, " ".join(args)))
        self.run("cd {} && make -j {}".format(self.source_dir, cpu_count()))
        self.run("cd {} && make install".format(self.source_dir))

    def package_info(self):
        libs = [
            'Concurrent',
            'Core',
            'DBus',
            'Gui',
            'Network',
            'OpenGL',
            'Sql',
            'Test',
            'Widgets',
            'Xml'
        ]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        for lib in libs:
            if self.settings.os == "Windows" and self.settings.build_type == "Debug":
                suffix = "d"
            elif self.settings.os == "Macos" and self.settings.build_type == "Debug":
                suffix = "_debug"
            else:
                suffix = ""
            self.cpp_info.libs += ["Qt5{}{}".format(lib, suffix)]
            self.cpp_info.includedirs += ["include/Qt{}".format(lib)]
        if self.settings.os == "Windows":
            # Some missing shared libs inside QML and others, but for the test
            # it works
            self.env_info.path.append(os.path.join(self.package_folder, "bin"))
