# Array ownership and NumPy exchange

Use this reference when the boundary exposes arrays, views, borrowed buffers or
zero-copy claims. Match the selected Rust NumPy crate, PyO3 and Python NumPy
versions before choosing conversion or borrowing APIs.

## Define the accepted representation

Trace the allocation owner and all views that can reach it. Establish dtype,
shape, strides/contiguity, alignment and mutability from the public contract.
Check whether conversion copies, coerces values or changes observable errors.
An accepted NumPy view need not be contiguous, and two distinct array objects
can overlap the same allocation. Treat writable output separately from input.

Keep the owner alive for every retained view. Returning memory allocated by Rust
requires a Python-visible owner or an ownership transfer supported by the
selected API; a pointer to a temporary Rust allocation is not a valid result.
Likewise, retaining a raw pointer does not extend a Python allocation's lifetime.
For object-containing arrays, account for Python object access and reference
ownership rather than treating elements as independent Rust bytes.

## Separate borrowing from synchronization

Use the binding's checked readonly/readwrite borrowing APIs where applicable.
Their checks protect participating Rust code against conflicting overlapping
borrows; Python, callbacks, unsafe Rust and other native code can still violate
the assumptions. Borrow guards do not coordinate threads by blocking access.

Detaching from Python does not end an active NumPy borrow or establish exclusive
access to the allocation. Before using Python-backed data during detached or
parallel work, establish owner lifetime and a mutation discipline covering every
possible accessor. The GIL is insufficient when native code or a free-threaded
interpreter can access that data concurrently.

Choose a copy when the required lifetime, layout or mutation discipline cannot
be established. Measure whether zero-copy improves the complete caller workload;
do not make it a goal that overrides a safe, understandable ownership boundary.
Record any deliberate copying or coercion as part of the interface decision.

## Focused verification

Select cases that distinguish the changed behavior: empty arrays, shape/dtype
mismatches, non-contiguous slices, overlapping input/output views and ownership
after the original input reference is dropped. Include concurrent mutation only
where concurrency is part of the supported contract. Verify both correct output
and the intended rejection/error for unsupported representations.

## Official sources

Use documentation for the selected crate versions; these versioned sources were
reviewed as an example of the current APIs, not a required upgrade.

- [Rust NumPy borrow checks and their limitations](https://docs.rs/numpy/0.30.0/numpy/borrow/index.html)
- [Rust NumPy array API](https://docs.rs/numpy/0.30.0/numpy/array/struct.PyArray.html)
- [PyO3 owning and borrowed Python handles](https://github.com/PyO3/pyo3/blob/v0.30.1/guide/src/types.md)
- [NumPy ndarray memory representation](https://numpy.org/doc/stable/reference/arrays.ndarray.html)
