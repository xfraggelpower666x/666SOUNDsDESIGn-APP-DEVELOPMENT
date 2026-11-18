"""Baut 666DEV Windows Control als eigenständiges Windows-x64-Archiv."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from hashlib import file_digest
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://github.com/xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT.git"
RUNTIMES = {
    "python": (
        "https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip",
        "90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159",
    ),
    "git": (
        "https://github.com/git-for-windows/git/releases/download/v2.56.1.windows.1/MinGit-2.56.1-64-bit.zip",
        "4a92850b6e917da4fd010669b614b55dccf5b0ec333a534cc4be4700dfefdafd",
    ),
    "gh": (
        "https://github.com/cli/cli/releases/download/v2.105.0/gh_2.105.0_windows_amd64.zip",
        "8813a72c899900afaa10e3fec8fbc64b908c89dbfe837e95ed2fa500fc140627",
    ),
}


def digest(file: Path) -> str:
    with file.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def runtime_zip(cache: Path, url: str, checksum: str) -> Path:
    cached = cache / url.rsplit("/", 1)[-1]
    if cached.is_file() and digest(cached) == checksum:
        return cached
    request = Request(url, headers={"User-Agent": "666DEV-Windows-Builder"})
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        partial = Path(temporary) / cached.name
        with urlopen(request, timeout=90) as stream, partial.open("wb") as output:
            shutil.copyfileobj(stream, output)
        if digest(partial) != checksum:
            raise ValueError(f"SHA-256 stimmt nicht: {cached.name}")
        partial.replace(cached)
    return cached


def run(*command: str | Path, cwd: Path = ROOT, env: dict | None = None) -> str:
    return subprocess.check_output([str(item) for item in command], cwd=cwd, env=env, text=True).strip()


def git_checkout(destination: Path, revision: str) -> None:
    git_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    git_env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_LFS_SKIP_SMUDGE="1")
    run("git", "init", "--quiet", "--template=", "--initial-branch=666DEV-windows", destination, env=git_env)
    run("git", "config", "core.autocrlf", "false", cwd=destination, env=git_env)
    run("git", "config", "core.filemode", "false", cwd=destination, env=git_env)
    run("git", "fetch", "--quiet", "--no-tags", ROOT, revision, cwd=destination, env=git_env)
    run("git", "checkout", "--quiet", "-B", "666DEV-windows", revision, cwd=destination, env=git_env)
    run("git", "remote", "add", "origin", ORIGIN, cwd=destination, env=git_env)
    if run("git", "rev-parse", "HEAD", cwd=destination, env=git_env) != revision:
        raise ValueError("Paket-Checkout hat einen abweichenden Commit.")
    if run("git", "status", "--porcelain", cwd=destination, env=git_env):
        raise ValueError("Paket-Checkout ist nicht sauber.")


def prepare_runtime(stage: Path, cache: Path) -> None:
    for name, (url, checksum) in RUNTIMES.items():
        print(f"{name}: prüfe und entpacke die Windows-x64-Laufzeit", flush=True)
        with ZipFile(runtime_zip(cache, url, checksum)) as archive:
            archive.extractall(stage / "runtime" / name)
    runtime = stage / "runtime"
    # Die isolierte Python-Laufzeit kennt denselben Quellbaum auch bei CLI-Unterprozessen.
    with (runtime / "python" / "python314._pth").open("a", encoding="ascii") as stream:
        stream.write("\n../../checkout/src\n")
    for relative in ("python/python.exe", "git/cmd/git.exe", "gh/bin/gh.exe"):
        if not (runtime / relative).is_file():
            raise ValueError(f"Runtime-Datei fehlt: {relative}")


def build(output: Path, cache: Path, go: str) -> Path:
    revision = run("git", "rev-parse", "HEAD^{commit}")
    version = run(go, "version")
    output.parent.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="666DEV portable ", dir=output.parent) as temporary:
        staging = Path(temporary)
        stage = staging / "666DEV Windows x64"
        stage.mkdir()
        git_checkout(stage / "checkout", revision)
        prepare_runtime(stage, cache)
        go_env = {**os.environ, "GOOS": "windows", "GOARCH": "amd64", "CGO_ENABLED": "0", "GOTOOLCHAIN": "local"}
        launcher = stage / "checkout" / "windows-app" / "portable" / "launcher.go"
        run(go, "build", "-trimpath", "-buildvcs=false", "-o", stage / "666DEV.exe", launcher, env=go_env)
        go_root = Path(run(go, "env", "GOROOT"))
        for notice in ("LICENSE", "PATENTS"):
            shutil.copyfile(go_root / notice, stage / f"GO-{notice}.txt")
        shutil.copyfile(launcher.with_name("START-HERE.txt"), stage / "START-HERE.txt")
        info = {"commit": revision, "platform": "windows-amd64", "launcher_go": version,
                "runtimes": {name: {"url": url, "sha256": checksum}
                             for name, (url, checksum) in RUNTIMES.items()}}
        (stage / "BUILD-INFO.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
        candidate = staging / output.name
        with ZipFile(candidate, "w", ZIP_DEFLATED, compresslevel=5) as archive:
            for path in sorted(stage.rglob("*")):
                archive.write(path, path.relative_to(staging))
        with ZipFile(candidate) as archive:
            damaged = archive.testzip()
        if damaged:
            raise ValueError(f"ZIP-Prüfung fehlgeschlagen: {damaged}")
        candidate.replace(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=ROOT / ".work" / "windows-runtime")
    parser.add_argument("--go", default="go", help="Pfad zur Go-Toolchain")
    args = parser.parse_args()
    output = build(args.output.resolve(), args.cache.resolve(), args.go)
    print(f"{digest(output)}  {output.name}")


if __name__ == "__main__":
    main()
