"""Target: what filespec's Directory and MultipleNotes should get out of wide_events.

An abstract copy of infra/libs/filespec (base.py, directory.py, multiple.py): pathlib instead of UPath, no media
types or fs transactions, the Increment folded into the Template, but the same load flow. Every `# TODO: Wide Event`
and `# WIDE_EVENT:` marker of the original is filled in with the wide_events call it should become.

Calls marked PROPOSED don't exist in wide_events yet; they are stubbed below so the file runs:

    uv run python docs/prototypes/filespec_target.py

The shape this produces: each Directory is one level of the event, named by its field; its files report into
its `node` block instead of getting a level of their own. Calls on an already loaded node (create, get, the
checksum on commit) run in the caller's event, so they land under `filespec.<directory name>`:

    {
      "workspace": {                                  <- named by the app: `with nested_event("workspace")`
        "node": {"type": "RootDir", "existed": true, "stray": ["notes.txt"], "checks": {...}},
        "reports": {
          "node": {"type": "Reports", "template": "report-{key}.json", "keys": [1], "stray": []}
        },
        "subfolder": {
          "node": {"type": "SubFolder", "existed": false, "created": [".checksum", "file.txt", "hash_file"],
                   "checksum": {"algo": "blake2b", "status": "unwritten"}}
        }
      },
      "filespec": {
        "sub_folder": {"node": {"type": "SubFolder", "checksum": {"status": "written", "files": 2}}},
        "reports": {"node": {"type": "Reports", "create": [2], "created": ["report-2.json"]}}
      }
    }

A failing load still writes its event, with the error at the level it was raised in:

    "subfolder": {"node": {..., "checksum": {"status": "mismatch", "mismatched": ["file.txt"]}},
                  "error": {"type": "ChecksumError", "message": "...", "stack": "Traceback ..."}}

What wide_events has to provide for this, i.e. the goal of the implementation:

1. A nested event named at runtime (PROPOSED `nested_event(*names)`). `log_event(name)` takes its name at
   decoration time, but a directory's name is its field name, which only the parent knows while it loads.
2. A nested event that merges on a raise too, records the error once at the innermost level, and restores the
   outer event. Today `log_event` merges nothing on a raise and leaves the ContextVars set.
3. A top-level event that is written on a raise too (PROPOSED `wide_event()`). Today
   `WideEvent.wrap` writes nothing then, but a failed load is the event you most want to read.
4. Nothing more from blocks and checks: `EventBlock` with `parent`, `append_list` and `from_kwargs`,
   `TimerEventBlock.timer` and `Checks`/`MultiCheckResult.dump()` already cover every other marker.

Open questions this raises:

- Width: `keys` lists every note of a MultipleNotes. With thousands of notes, a count (or first/last key) may
  be enough. Likewise the full `MultiCheckResult.dump()` (~15 lines per directory) when all checks passed.
- Should `load` without an open event be silent (as now: the fields are lost) or warn?
- Calls on a loaded node land under `filespec.<path.name>`, while `load` uses field names. Remembering the field
  name on the node would make both agree.
"""
import hashlib
import json
import tempfile
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, fields
from functools import cache
from pathlib import Path
from typing import Any, ClassVar

from wide_events import Checks, ContextBlock, ContextEvent, EventBlock, ExceptionEvent, InlineCheck, TimerEventBlock
from wide_events.log import FileMirrorLogHandler, LogClass, LogConfig, VerboseConsoleLogHandler, divider


# --- PROPOSED wide_events API, stubbed ---------------------------------------------------------------------------

def _record_error(exc:Exception):
    """Write `exc` as `error` on the current event, only on the level it was raised in."""
    if getattr(exc, "_wide_events_recorded", False):
        return
    ExceptionEvent.save_error(type(exc).__name__, str(exc), "".join(traceback.format_exception(exc)))
    exc._wide_events_recorded = True

@contextmanager
def nested_event(*names:str):
    """`log_event` as a with-block: its fields merge into the outer event under `names`, also when it raises."""
    event, blocks = ContextEvent.init(), ContextBlock.init()
    try:
        yield
    except Exception as exc:
        _record_error(exc)
        raise
    finally:
        payload = event.drop()
        blocks.drop()
        for name in reversed(names):
            payload = {name:payload}
        ContextEvent.update(payload, append_lists=True)

@contextmanager
def wide_event():
    """`WideEvent.wrap` as a with-block that writes the event also when it raises."""
    event, blocks = ContextEvent.init(), ContextBlock.init()
    try:
        yield
    except Exception as exc:
        _record_error(exc)
        raise
    finally:
        payload = event.drop()
        blocks.drop()
        LogClass.file_logger().info("wide_event", **payload)


# --- Blocks: exist today ---------------------------------------------------------------------------------------

class NodeBlock(EventBlock):
    """The node of one level of the tree: a Directory, with its files reporting into it."""

    namespace = "node"
    append_list = True

class ChecksumBlock(TimerEventBlock):
    """The checksum check of a ChecksumDirectory, nested in its node."""

    namespace = "checksum"
    parent = NodeBlock


# --- filespec, abstract ----------------------------------------------------------------------------------------

class ChecksumError(Exception):
    ...

@dataclass
class BaseNode(LogClass):
    path:Path

    is_directory:ClassVar[bool] = False

    @classmethod
    def load(cls, path:Path|str):
        raise NotImplementedError()

    @staticmethod
    def load_path(path:Path|str) -> Path:
        if isinstance(path, (Path, str)):
            return Path(path)
        # TODO: Wide Event for the error -> nothing to write here, the raise lands as `error` on the current level
        raise TypeError(f"Unsupported Type {type(path)} for Path")

    @classmethod
    def verify_existence(cls, path:Path) -> bool:
        """Create `path` if it is missing; return whether it existed, which the caller writes to its level."""
        # WIDE_EVENT: DIRECTORY_EXISTS -> returned, a Directory writes `existed`, a File `created`
        if path.exists():
            return True
        cls.console_logger.warning(f"{path} does not exist, creating it")
        cls.create_path(path)
        return False

    @staticmethod
    def create_path(path:Path):
        raise NotImplementedError()

    @classmethod
    @cache
    def return_node_fields(cls) -> dict[Any, type["BaseNode"]]:
        return {
            field:field.type for field in fields(cls)
            if isinstance(field.type, type) and issubclass(field.type, BaseNode)
        }

    @contextmanager
    def op_event(self):
        """The level for a call on a loaded node, which runs in the caller's event, not in the one of `load`."""
        with nested_event("filespec", self.path.name):
            NodeBlock.from_kwargs(type=type(self).__name__, path=str(self.path))
            yield

@dataclass
class File(BaseNode):

    @classmethod
    def load(cls, path:Path|str):
        path = cls.load_path(path)
        # A file has no level of its own, it reports into the node of its directory
        if not cls.verify_existence(path):
            NodeBlock.from_kwargs(created=[path.name])
        return cls(path)

    @staticmethod
    def create_path(path:Path):
        path.touch()

    def load_file(self):
        return self.path.read_text()

    def save_file(self, data:str):
        self.path.write_text(data)

@dataclass
class JsonFile(File):
    """Stands in for `Annotated[MediaFile, MediaType.APPLICATION_JSON, JsonOperation(indent=4)]`."""

    def load_file(self):
        data = super().load_file()
        return json.loads(data) if data else {}

    def save_file(self, data:Any):
        super().save_file(json.dumps(data, indent=4))


def fields_are_nodes(cls:type[BaseNode]) -> bool:
    """Whether every field besides `path` is a node, so no field is skipped silently by `load`."""
    node_fields = cls.return_node_fields()
    return all(field.name == "path" or field in node_fields for field in fields(cls))

@dataclass
class Directory(BaseNode):

    is_directory = True
    field_checks:ClassVar[Checks] = Checks((InlineCheck(["cls"], fields_are_nodes),))

    @classmethod
    def load(cls, path:Path|str):
        # TODO: Setup Wide Events -> the parent opened this level; the root's is opened by the app
        path = cls.load_path(path)
        existed = cls.verify_existence(path)
        NodeBlock.from_kwargs(type=cls.__name__, path=str(path), existed=existed)

        # TODO: Check if types have been set -> Checks library -> Log
        checks = cls.field_checks(cls=cls)
        NodeBlock.from_kwargs(checks=checks.dump())
        if not checks.ok:
            cls.console_logger.warning(f"{cls.__name__} has fields that are not nodes, they are not loaded")

        _fields = {
            field.default if isinstance(field.default, str) else field.name : (node_type, field.name)
            for field, node_type in cls.return_node_fields().items()
        }

        stray = sorted({child.name for child in path.iterdir()} - set(_fields.keys()))
        if stray:
            cls.console_logger.warning(f"Stray files located in '{str(path)}':{stray}")
        # TODO: Wide Event for stray directories
        NodeBlock.from_kwargs(stray=stray)

        args = {}
        for file_name, (_type, field_name) in _fields.items():
            if _type.is_directory:
                # A directory is a level of its own, named by its field
                with nested_event(field_name):
                    args[field_name] = _type.load(path / file_name)
            else:
                args[field_name] = _type.load(path / file_name)

        return cls(path, **args)

    @classmethod
    @cache
    def return_files(cls):
        return [field for field, _cls in cls.return_node_fields().items() if not _cls.is_directory]

    @staticmethod
    def create_path(path:Path):
        path.mkdir()

    # The fs transaction of the original is left out, only its hooks stay
    def __enter__(self):
        self.on_start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.on_commit()

    def on_start(self):
        ...

    def on_commit(self):
        ...

@dataclass
class ChecksumDirectory(Directory):

    checksum:JsonFile = ".checksum"

    @classmethod
    def load(cls, path:Path|str):
        _cls:"ChecksumDirectory" = super().load(path)
        _cls.verify_checksum()
        return _cls

    def verify_checksum(self):
        # TODO: Wide Event the Checksums
        block = ChecksumBlock.from_kwargs(algo=self.hash_algo)
        checksum_disk = self.get_checksum()
        if not checksum_disk:
            block.set(status="unwritten")
            return

        with block.timer("hash"):
            checksum_real = self.compute_checksum()
        mismatched = sorted(name for name, _hash in checksum_real.items() if checksum_disk.get(name) != _hash)
        block.set(files=len(checksum_real), mismatched=mismatched)

        if mismatched:
            # TODO: Better ChecksumError // Wide Event -> the mismatch is in the block, the raise becomes `error`
            block.set(status="mismatch")
            raise ChecksumError(f"{mismatched} in '{self.path}' differ from the stored checksum")
        block.set(status="verified")

    @property
    def hash_algo(self):
        # TODO: Wide Event the algo -> written by verify_checksum and write_checksum; blake3 in the original
        return "blake2b"

    def compute_checksum(self) -> dict:
        return {
            file.path.name: hashlib.blake2b(file.path.read_bytes()).hexdigest()
            for file in [getattr(self, x.name) for x in self.return_files() if x.name != "checksum"]
        }

    def write_checksum(self):
        with self.op_event():
            checksum = self.compute_checksum()
            self.checksum.save_file(checksum)
            ChecksumBlock.from_kwargs(algo=self.hash_algo, status="written", files=len(checksum))

    def get_checksum(self) -> dict:
        return self.checksum.load_file()

    def on_commit(self):
        self.write_checksum()


@dataclass
class Template:
    """`report-{key}.json` with integer keys counting up from 1, the `Counter` increment of the original."""

    base_str:str

    def get(self, key:int) -> str:
        return self.base_str.format(key=key)

    def new(self, existing) -> tuple[str, int]:
        key = max(existing, default=0) + 1
        return self.get(key), key

    def claims(self, name:str) -> int|None:
        prefix, _, suffix = self.base_str.partition("{key}")
        if not (name.startswith(prefix) and name.endswith(suffix)):
            return None
        key = name[len(prefix):len(name) - len(suffix)]
        return int(key) if key.isdigit() else None

@dataclass
class MultipleNotes(Directory):

    template:Template
    increments:dict[int, BaseNode]

    base_str:ClassVar[str]
    _multiple_type:ClassVar[type[BaseNode]] = File

    @classmethod
    def load(cls, path:Path|str):
        path = cls.load_path(path)
        existed = cls.verify_existence(path)
        template = Template(cls.base_str)
        NodeBlock.from_kwargs(type=cls.__name__, path=str(path), existed=existed, template=cls.base_str)

        claims = {child.name:template.claims(child.name) for child in path.iterdir()}
        stray = sorted(name for name, key in claims.items() if key is None)
        if stray:
            cls.console_logger.warning(f"Stray files located in '{str(path)}':{stray}")

        # The notes are files, so they report into this level: their keys, not one level per note
        increments = {
            key:cls._multiple_type.load(path / name)
            for name, key in claims.items() if key is not None
        }
        NodeBlock.from_kwargs(stray=stray, keys=sorted(increments))

        return cls(path, template, increments)

    def create(self, increment:int|None=None):
        # TODO: Add Wide Events
        with self.op_event():
            if increment is None:
                name, increment = self.template.new(self.increments.keys())
            else:
                name = self.template.get(increment)
            NodeBlock.from_kwargs(create=[increment])
            # Writes `created` into this level if the note is new
            file = self._multiple_type.load(self.path / name)
            self.increments[increment] = file
        return file

    def get(self, increment:int):
        # TODO: Add Wide Events -> a missing key raises KeyError, which lands as `error` on this level
        with self.op_event():
            NodeBlock.from_kwargs(get=[increment])
            return self.increments[increment]


# --- Sample usage ----------------------------------------------------------------------------------------------

@dataclass
class SubFolder(ChecksumDirectory):
    file:File = "file.txt"
    hash_file:File = "hash_file"

@dataclass
class Reports(MultipleNotes):
    base_str = "report-{key}.json"

@dataclass
class RootDir(Directory):
    reports:Reports
    subfolder:SubFolder = "sub_folder"


class TargetLog(LogConfig):
    name = "filespec-target"
    handlers = (VerboseConsoleLogHandler, FileMirrorLogHandler)


def main():
    TargetLog.configure()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "notes.txt").write_text("not a report")
        (root / "reports").mkdir()
        (root / "reports" / "report-1.json").write_text("{}")

        divider("1. first load: sub_folder is created, the checksum is written on commit")
        with wide_event():
            with nested_event("workspace"):
                root_dir = RootDir.load(root)
            with root_dir.subfolder:
                root_dir.subfolder.file.save_file("hello world")
            root_dir.reports.create()

        divider("2. second load: the checksum is verified and timed")
        with wide_event():
            with nested_event("workspace"):
                root_dir = RootDir.load(root)
            root_dir.reports.get(2)

        divider("3. tampered file: the ChecksumError lands at workspace.subfolder")
        (root / "sub_folder" / "file.txt").write_text("tampered")
        try:
            with wide_event(), nested_event("workspace"):
                RootDir.load(root)
        except ChecksumError:
            pass


if __name__ == "__main__":
    main()
