"""Utilities for working with collection types."""


def list_splitter(sequence, nentries):
    """Split sequence into groups."""
    # iterable must be of type Sequence
    for i in xrange(0, len(sequence), nentries):
        yield sequence[i:i + nentries]


def subdict(dct, seq, **kwargs):
    """Return a sub dict. optionally with extra entries."""
    # tuple(seq) as seq might be iterator
    # return {k: v for k, v in dct.iteritems() if k in tulpe(seq)}

    # This might be faster if dct is large as doesn't have to iterate through it.
    # also works natively with seq being an iterator, no tuple initialisation
    return dict({key: dct[key] for key in seq if key in dct}, **kwargs)
