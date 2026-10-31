# Mojo and Python interop patterns

These examples describe the pinned upstream snapshot. Confirm imports, PythonObject
conversion signatures, module builders, pointer/origin types and extension build
flags against the project-selected Mojo SDK/channel and Python runtime/ABI. The
selected environment manager, dependency constraints and target architecture remain
authoritative. WRONG/CORRECT labels are conditional on that compatibility check.

Load only the affected direction or operation. Code evaluation/imports execute
code; dynamic input must stay data. SDK absence or an untested ABI is a capability
gap, not proof that these examples compile or load on the target.

## Using Python from Mojo

```mojo
from std.python import Python, PythonObject

var np = Python.import_module("numpy")
var arr = np.array([1, 2, 3])

# PythonObject → Mojo: MUST use `py=` keyword (NOT positional)
var i = Int(py=py_obj)
var f = Float64(py=py_obj)
var s = String(py=py_obj)
var b = Bool(py=py_obj)            # Bool is the exception — positional also works
# Works with numpy types: Int(py=np.int64(1)), Float64(py=np.float64(3.14))
```

| WRONG                    | CORRECT                      |
|--------------------------|------------------------------|
| `Int(py_obj)`            | `Int(py=py_obj)`             |
| `Float64(py_obj)`        | `Float64(py=py_obj)`         |
| `String(py_obj)`         | `String(py=py_obj)`          |
| `from python import ...` | `from std.python import ...` |

### Mojo → Python conversions

Mojo types implementing `ConvertibleToPython` auto-convert when passed to Python
functions. For explicit conversion: `value.to_python_object()`.

### Building Python collections from Mojo

```mojo
var py_list = Python.list(1, 2.5, "three")
var py_tuple = Python.tuple(1, 2, 3)
var py_dict = Python.dict(name="value", count=42)

# Python.dict() is generic over a single value type V for all kwargs.
# Mixed types fail because the compiler can't infer one V.
# WRONG:  Python.dict(flag=my_bool, count=42)
# CORRECT: Python.dict(flag=PythonObject(my_bool), count=PythonObject(42))

# Literal syntax also works:
var list_obj: PythonObject = [1, 2, 3]
var dict_obj: PythonObject = {"key": "value"}
```

### PythonObject operations

`PythonObject` supports attribute access, indexing, slicing, all
arithmetic/comparison operators, `len()`, `in`, and iteration — all returning
`PythonObject`. No need to convert to Mojo types for intermediate operations.

```mojo
# Iterate Python collections directly
for item in py_list:
    print(item)               # item is PythonObject

# Attribute access and method calls
var result = obj.method(arg1, arg2, key=value)

# None
var none_obj = Python.none()
var obj: PythonObject = None      # implicit conversion works
```

### Evaluating Python code

`Python.evaluate` executes code. Use trusted static source only; pass variable
values through object APIs or call arguments, never concatenate/interpolate them
into Python source. Imports also execute module code; resolve module names and
search paths from trusted project context. These examples are not a sandbox.

```mojo
# Expression
var result = Python.evaluate("1 + 2")

# Multi-line code as module (file=True)
var mod = Python.evaluate("def greet(n): return f'Hello {n}'", file=True)
var greeting = mod.greet("world")

# Add to Python path for local imports
Python.add_to_path("./my_modules")
var my_mod = Python.import_module("my_module")
```

### Exception handling

Python exceptions propagate as Mojo `Error`. Functions calling Python must be
`raises`:

```mojo
def use_python() raises:
    try:
        var result = Python.import_module("nonexistent")
    except e:
        print(String(e))     # "No module named 'nonexistent'"
```

### Common Python / Mojo interoperability patterns

```mojo
# Environment variables
# When native access fits the selected SDK and project convention:
# var os = Python.import_module("os")
# var val = os.environ.get("MY_VAR")

# Mojo native env var access via std.os (do not log secret values)
from std.os import getenv
var val = getenv("MY_VAR")  # returns Optional[String]
```

```mojo
# Sorting with custom key
# WRONG — Mojo has no lambda syntax
# var sorted = my_list.sort(key=lambda x: x["score"])

# Use a callable factory: field remains data, never Python source.
def sort_by_field(data: PythonObject, field: String) raises -> PythonObject:
    var builtins = Python.import_module("builtins")
    var operator = Python.import_module("operator")
    var key_fn = operator.itemgetter(field)
    return builtins.sorted(data, key=key_fn)
```

```mojo
# Dict .get() works on PythonObject
var name = data.get("name", PythonObject("unknown"))
var count = Int(py=data.get("count", PythonObject(0)))
```

## Calling Mojo from Python (extension modules)

For compatible SDKs, Mojo can build Python extension modules via
`PythonModuleBuilder`. Confirm the selected SDK's supported Python ABI, platform,
architecture, library format and module initialization/export rules before using
these examples. Preserve object ownership, reference lifetimes and exception
conversion across the boundary; a successful import alone is not full acceptance.
The snapshot pattern:

1. Define an `@export def PyInit_<module_name>() abi("C") -> PythonObject`
2. Use `PythonModuleBuilder` to register functions, types, and methods
3. Compile with `mojo build --emit shared-lib`
4. Import from Python (or use `import mojo.importer` for auto-compilation)

Calling convention: only `PyInit_<module>` needs `@export`, and it must be
`abi("C")` because the CPython runtime calls it directly across the C boundary
(so it can't `raises` — catch errors and `abort` instead). Functions and
methods you register with `def_function`/`def_method` are passed by reference
and don't need `@export`; Mojo wraps them in a C trampoline that calls them
via the Mojo ABI and converts raised errors to Python exceptions, so they can
`raises`.

### Exporting functions

```mojo
from std.os import abort
from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder

@export
def PyInit_my_module() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("my_module")
        m.def_function[add]("add")
        m.def_function[greet]("greet")
        return m.finalize()
    except e:
        abort(String("failed to create module: ", e))

# Functions take/return PythonObject. Up to 6 args with def_function.
def add(a: PythonObject, b: PythonObject) raises -> PythonObject:
    return a + b

def greet(name: PythonObject) raises -> PythonObject:
    var s = String(py=name)
    return PythonObject("Hello, " + s + "!")
```

### Exporting types with methods

```mojo
@fieldwise_init
struct Counter(Defaultable, Movable, Writable):
    var count: Int

    def __init__(out self):
        self.count = 0

    # Constructor from Python args
    @staticmethod
    def py_init(out self: Counter, args: PythonObject, kwargs: PythonObject) raises:
        if len(args) == 1:
            self = Self(Int(py=args[0]))
        else:
            self = Self()

    # Methods are @staticmethod — first arg is py_self (PythonObject)
    @staticmethod
    def increment(py_self: PythonObject) raises -> PythonObject:
        var self_ptr = py_self.downcast_value_ptr[Self]()
        self_ptr[].count += 1
        return PythonObject(self_ptr[].count)

    # Auto-downcast alternative: first arg is UnsafePointer[Self, MutAnyOrigin]
    @staticmethod
    def get_count(self_ptr: UnsafePointer[Self, MutAnyOrigin]) -> PythonObject:
        return PythonObject(self_ptr[].count)

@export
def PyInit_counter_module() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("counter_module")
        _ = (
            m.add_type[Counter]("Counter")
            .def_py_init[Counter.py_init]()
            .def_method[Counter.increment]("increment")
            .def_method[Counter.get_count]("get_count")
        )
        return m.finalize()
    except e:
        abort(String("failed to create module: ", e))
```

### Method signatures — two patterns

| Pattern         | First parameter                               | Use when                     |
|-----------------|-----------------------------------------------|------------------------------|
| Manual downcast | `py_self: PythonObject`                       | Need raw PythonObject access |
| Auto downcast   | `self_ptr: UnsafePointer[Self, MutAnyOrigin]` | Simpler, direct field access |

Both are registered with `.def_method[Type.method]("name")`.

### Kwargs support

```mojo
from std.collections import StringDict

# In a method:
@staticmethod
def config(
    py_self: PythonObject, kwargs: StringDict[PythonObject]
) raises -> PythonObject:
    for entry in kwargs.items():
        print(entry.key, "=", entry.value)
    return py_self
```

### Importing Mojo modules from Python

Where supported by the selected SDK, `mojo.importer` auto-compiles `.mojo`
files and writes cached results to `__mojocache__/`. Importing is execution with
filesystem/compiler side effects, not a read-only discovery check. Run only for
the authorized project using its compatible SDK and Python environment:

```python
import mojo.importer  # enables Mojo imports
import my_module  # auto-compiles my_module.mojo

print(my_module.add(1, 2))
```

The module name in `PyInit_<name>` must match the `.mojo` filename.

The `.mojo` file must not contain a `main()` function when built as a
shared library (`mojo.importer` or `--emit shared-lib`). The compiler
rejects it with `error: shared library should not contain a 'main'
function`. Keep test/CLI code in a separate file.

### Returning Mojo values to Python

```mojo
# Wrap a Mojo value as a Python object (for bound types)
return PythonObject(alloc=my_mojo_value^)    # transfer ownership with ^

# Recover the Mojo value later
var ptr = py_obj.downcast_value_ptr[MyType]()
ptr[].field    # access fields via pointer
```
