# Candidate rollback packet — `sig.candidate-rollback/1`

> Status: **prepared_not_needed** — the candidate is unpublished; this is
> a prepared pointer-reversal plan, not a mutation.

- publication `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587` · manifest `3966c7657b7b30b379c50608…`
- pointer unchanged by this build: `True`

## Reversal

pointer-only reversal through exports.release.rollback on the served registry — the mutable latest.json flips to the recorded prior pointer; the immutable r/<pub> namespace is never deleted (append-only release history)

no latest.json existed before this candidate — reversal removes the pointer entirely rather than fabricating a predecessor

1. confirm the candidate publication_id is currently pointed at
1. run exports.release.rollback(registry, to=<prior pointer>) or remove latest.json when no prior pointer existed
1. re-validate the registry (catalog + compatibility indexes)
1. leave the immutable r/<publication_id> tree untouched — it is history, and its manifest/descriptor remain verifiable

## Preconditions

- the candidate was actually activated by P32.25 (this build never activates — the packet is preparation, not a mutation)
- operator authorization under the HG-11/GATE-G3 chain
