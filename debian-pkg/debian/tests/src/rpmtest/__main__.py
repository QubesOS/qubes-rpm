"""A simple test suite for some RPM tools."""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

from typing import NamedTuple

import utf8_locale

PROG_NAME = "something"
PROG_VER = "1.0"
PROG_RELEASE = "1"

PROG_DIR = f"{PROG_NAME}-{PROG_VER}"
PROG_RPM = f"{PROG_DIR}-{PROG_RELEASE}"

RE_ARCH = re.compile(r"^ (?P<arch> [A-Za-z0-9._-]+ ) $", re.X)


class Config(NamedTuple):
    """Runtime configuration for the rpmtest tool."""

    bindir: pathlib.Path
    datadir: pathlib.Path
    utf8_env: dict[str, str]


def parse_args() -> Config:
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(prog="rpmtest")
    parser.add_argument(
        "-b",
        "--bindir",
        type=pathlib.Path,
        required=True,
        help="The directory to find the RPM programs in",
    )
    parser.add_argument(
        "-d",
        "--datadir",
        type=pathlib.Path,
        required=True,
        help="The directory to find the test data in",
    )

    args = parser.parse_args()

    # Some basic validation
    rpm = args.bindir / "rpm"
    if not rpm.is_file() or (rpm.stat().st_mode & 0o0111) != 0o0111:
        sys.exit(f"Not an executable file: {rpm}; is --bindir specified correctly?")
    makefile = args.datadir / PROG_DIR / "Makefile"
    if not makefile.is_file() or (makefile.stat().st_mode & 0o0444) != 0o0444:
        sys.exit(f"Not a readable file: {makefile}; is --datadir specified correctly?")

    return Config(
        bindir=args.bindir.absolute(),
        datadir=args.datadir.absolute(),
        utf8_env=utf8_locale.UTF8Detect().detect().env,
    )


def get_rpm_arch(cfg: Config) -> list[str]:
    """Query the RPM tool for its target architecture."""
    print("Querying `rpm` for the target architecture")
    lines = subprocess.check_output(
        [cfg.bindir / "rpm", "--eval", "%{_arch}"], encoding="UTF-8", env=cfg.utf8_env
    ).splitlines()
    if len(lines) != 1:
        sys.exit(f"Expected a single line of output from `rpm --eval`, got {lines!r}")
    arch_data = RE_ARCH.match(lines[0])
    if not arch_data:
        sys.exit(f"Unexpected `rpm --eval` output: {lines[0]!r}")
    arch = arch_data.group("arch")
    print(f"Got architecture {arch!r}")

    template = f"%{{{arch}}}"
    print(f"Checking whether {template} is actually a family of architectures")
    lines = subprocess.check_output(
        [cfg.bindir / "rpm", "--eval", template], encoding="UTF-8", env=cfg.utf8_env
    ).splitlines()
    if len(lines) != 1:
        sys.exit(f"Expected a single line of output from `rpm --eval`, got {lines!r}")
    arches = lines[0].split()
    if arches == [template]:
        print(f"No, apparently {arch} is a single architecture name")
        return [arch]
    if not arches or not all(RE_ARCH.match(word) for word in arches):
        sys.exit(f"Unexpected `rpm --eval` output: {lines[0]!r}")

    return arches


def pack_up(cfg: Config, tempd: pathlib.Path) -> pathlib.Path:
    """Pack the program source up into a tarball."""
    tarball = tempd / f"{PROG_DIR}.tar.gz"
    print(f"Packing {PROG_DIR} up into {tarball}")
    subprocess.check_call(
        ["tar", "-caf", tarball, "-C", cfg.datadir, "--", PROG_DIR], env=cfg.utf8_env
    )
    if not tarball.is_file():
        sys.exit(f"`tar -caf` did not create {tarball}")
    subprocess.check_call(["ls", "-l", "--", tarball], env=cfg.utf8_env)

    return tarball


def build_srpm(cfg: Config, tempd: pathlib.Path, tarball: pathlib.Path) -> pathlib.Path:
    """Build a source RPM package."""
    specfile = cfg.datadir / f"{PROG_NAME}.spec"
    srcdir = tempd / "source"
    srcdir.mkdir(mode=0o755)

    (srcdir / "SOURCES").mkdir(mode=0o755)
    tarball.rename(srcdir / "SOURCES" / tarball.name)

    print(f"Building a source RPM package in {srcdir}")
    subprocess.check_call(
        [cfg.bindir / "rpmbuild", "-bs", f"-D_topdir {srcdir}", "--", specfile],
        cwd=srcdir,
        env=cfg.utf8_env,
    )

    srpmdir = srcdir / "SRPMS"
    print(f"Making sure there is stuff in {srpmdir}")
    items = list(srpmdir.iterdir())
    if len(items) != 1:
        sys.exit(f"Expected a single file in {srpmdir}, got {items!r}")
    srpm = items[0]
    if not srpm.is_file() or srpm.name != f"{PROG_RPM}.src.rpm":
        sys.exit(f"Expected {PROG_RPM}.src.rpm in {srpmdir}, got {srpm!r}")
    print(f"Found {srpm}")

    return srpm


def build_rpm(
    cfg: Config, tempd: pathlib.Path, srpm: pathlib.Path, arches: list[str]
) -> tuple[pathlib.Path, str]:
    """Build a binary RPM package."""
    srcdir = tempd / "build"
    srcdir.mkdir(mode=0o755)

    print(f"Building a binary RPM package in {srcdir}")
    subprocess.check_call(
        [
            "fakeroot",
            cfg.bindir / "rpmbuild",
            "--rebuild",
            f"-D_topdir {srcdir}",
            "--",
            srpm,
        ],
        cwd=srcdir,
        env=cfg.utf8_env,
    )

    rpmdir = srcdir / "RPMS"
    print(f"Making sure there is stuff in {rpmdir}")
    subprocess.check_call(["find", "--", rpmdir, "-ls"], env=cfg.utf8_env)
    items = list(rpmdir.iterdir())
    if len(items) != 1:
        sys.exit(f"Expected a single arch directory in {rpmdir}, got {items!r}")
    archdir = items[0]
    arch = archdir.name
    if not archdir.is_dir() or arch not in arches:
        sys.exit(f"Expected an {arches!r} directory in {rpmdir}, got {items!r}")

    expected_name = f"{PROG_RPM}.{arch}.rpm"
    items = list(archdir.iterdir())
    if len(items) != 1:
        sys.exit(f"Expected a single RPM file in {archdir}, got {items!r}")
    rpm = items[0]
    if not rpm.is_file() or rpm.name != expected_name:
        sys.exit(f"Expected {expected_name} in {archdir}, got {rpm!r}")
    print(f"Found {rpm}")

    return rpm, arch


def check_rpm(cfg: Config, rpm: pathlib.Path, arches: list[str], source: bool) -> None:
    """Examine the RPM file."""
    print(f"Examining an RPM package file: {rpm}")
    lines = subprocess.check_output(
        [
            cfg.bindir / "rpm",
            "-qpf",
            rpm,
            "--qf",
            r"%{Name}\t%{Epoch}\t%{Version}\t%{Release}\t%{Arch}\t%{Source}\n",
        ],
        encoding="UTF-8",
        env=cfg.utf8_env,
    ).splitlines()
    print(f"- got rpm -qpf output {lines!r}")
    if len(lines) != 1:
        sys.exit(f"Expected a single line of output from `rpm -qpf {rpm}`, got {lines!r}")
    fields = lines[0].split("\t")
    expected = [
        PROG_NAME,
        "(none)",
        PROG_VER,
        PROG_RELEASE,
        "<arch>",
        f"{PROG_DIR}.tar.gz" if source else "(none)",
    ]
    if len(fields) < 5 or fields[4] not in arches:
        sys.exit(f"Expected `rpm -qpf {rpm}` to produce {expected!r}, got {fields!r}")
    expected[4] = fields[4]
    if fields != expected:
        sys.exit(f"Expected `rpm -qpf {rpm}` to produce {expected!r}, got {fields!r}")


def check_rpm_contents(cfg: Config, rpm: pathlib.Path, source: bool) -> None:
    """Examine the RPM file."""
    print("Examining the contents of an RPM file")
    lines = subprocess.check_output(
        ["rpm", "-qplf", rpm], encoding="UTF-8", env=cfg.utf8_env
    ).splitlines()
    print(f"- got {lines!r}")
    expected = (
        [f"{PROG_DIR}.tar.gz", f"{PROG_NAME}.spec"]
        if source
        else [f"/usr/bin/{PROG_NAME}", f"/usr/share/doc/{PROG_NAME}/README"]
    )
    if lines != expected:
        sys.exit(f"Expected `rpm -qplf` to output {expected!r}, got {lines!r}")


def install_rpm(cfg: Config, tempd: pathlib.Path, rpm: pathlib.Path, arch: str) -> None:
    """Install the RPM into a temporary root directory."""
    rootdir = tempd / "root"
    rootdir.mkdir(mode=0o755)
    print(f"Expecting the installation of {rpm} into {rootdir} to fail")
    with subprocess.Popen(
        ["rpm", "-ivh", "-r", rootdir, "--", rpm],
        bufsize=0,
        encoding="UTF-8",
        env=cfg.utf8_env,
        stderr=subprocess.PIPE,
    ) as proc:
        _, errs = proc.communicate()
        if (
            "Failed dependencies:" not in errs
            or f"/bin/sh is needed by {PROG_NAME}-{PROG_VER}" not in errs
        ):
            sys.exit(f"Expected `rpm -i` to complain about /bin/sh, got error output: {errs!r}")

    print("Making sure the directory is empty except maybe for /home")
    lines = sorted(str(path) for path in rootdir.iterdir() if path.name not in ("home", "root"))
    if lines:
        sys.exit(f"Expected {rootdir} to be empty, got {lines!r}")

    print(f"Installing {rpm} into {rootdir} using `--nodeps`")
    subprocess.check_call(["rpm", "-ivh", "-r", rootdir, "--nodeps", "--", rpm], env=cfg.utf8_env)

    print("Making sure some files were installed")
    lines = sorted(str(path) for path in rootdir.rglob("*"))
    if (
        str(rootdir / "usr/bin" / PROG_NAME) not in lines
        or str(rootdir / "usr/share/doc" / PROG_NAME / "README") not in lines
    ):
        sys.exit(f"Missing files that should have been installed, got {lines!r}")

    print("Querying the list of installed packages")
    lines = subprocess.check_output(
        ["rpm", "-qa", "-r", rootdir], encoding="UTF-8", env=cfg.utf8_env
    ).splitlines()
    print(f"- got {lines!r}")
    expected = [f"{PROG_NAME}-{PROG_VER}-{PROG_RELEASE}.{arch}"]
    if lines != expected:
        sys.exit(f"Expected `rpm -qa` to output {expected!r}, got {lines!r}")

    print("Querying the list of files installed by the package")
    lines = subprocess.check_output(
        ["rpm", "-ql", "-r", rootdir, "--", PROG_NAME],
        encoding="UTF-8",
        env=cfg.utf8_env,
    ).splitlines()
    print(f"- got {lines!r}")
    expected = [f"/usr/bin/{PROG_NAME}", f"/usr/share/doc/{PROG_NAME}/README"]
    if lines != expected:
        sys.exit(f"Expected `rpm -ql` to output {expected!r}, got {lines!r}")


def main() -> None:
    """Main program: parse command-line options, run tests."""
    cfg = parse_args()
    with tempfile.TemporaryDirectory() as tempd_obj:
        tempd = pathlib.Path(tempd_obj)
        print(f"Using {tempd} as a temporary directory")
        arches = get_rpm_arch(cfg)
        print(f"Got architectures: {arches}")
        tarball = pack_up(cfg, tempd)
        srpm = build_srpm(cfg, tempd, tarball)
        check_rpm(cfg, srpm, arches, True)
        check_rpm_contents(cfg, srpm, True)
        rpm, arch = build_rpm(cfg, tempd, srpm, arches)
        check_rpm(cfg, rpm, [arch], False)
        check_rpm_contents(cfg, rpm, False)
        install_rpm(cfg, tempd, rpm, arch)
        print("Everything seems fine!")


if __name__ == "__main__":
    main()
