# Alpha4 release and full megacut rebuild

## Goal

Produce the next alpha release of *Seven Days to the Wolves* as a rebuilt,
verified 18-item megacut, using the current act-II-updated checkout as the
release source while preserving all authored work found in other worktrees.

The release identifier is `alpha4`. The canonical running order, item count,
trim points, authored copy, and delivery layout remain unchanged.

## Release flow

1. Inspect every linked worktree and its branch.
2. Preserve coherent uncommitted work by committing it on its named branch and
   pushing that branch. If a branch's remote is gone, push a named rescue branch
   before removing or cleaning anything. Do not discard ambiguous changes.
3. Create `release/alpha4` from the current clean checkout.
4. Update the megacut manifest's `_version` with the alpha4 release note. Do
   not hand-edit derived fields, delivery digests, generated catalogs, or
   rendered artifacts.
5. Run the positive freshness proof:

   ```bash
   python3 tools/deliver.py status --check
   python3 tools/megacut.py stories/megacut/megacut.json --dry-run
   ```

6. Rebuild every stale act and dependent delivery artifact through the
   repository builders. Encoding is remote-first: use the Kubernetes farm when
   reachable, and use only the repository's capped local fallback when the
   cluster is unavailable, with the reason printed.
7. Publish rebuilt acts, assemble the megacut, and verify the delivered output.
8. Run the complete offline validation sequence and push `release/alpha4`.
   `main` is not pushed directly.

## Bug sweep

The sweep covers:

- the release diff and all preserved worktree diffs;
- delivery freshness, provenance, hardlink, checksum, and social-copy reports;
- megacut dry-run graph and canonical 18-item scope;
- farm-policy and targeted delivery/megacut tests;
- the full offline pytest suite;
- corpus, rederived-field, generated-enum, generated-skill-catalog, and
  pre-commit checks.

Before each encode, cluster reachability and remote selection are verified.
After each encode, the workflow result and actual output path are checked.
The assembled programme is checked for expected duration, joins, stream
metadata, ffprobe decode success, audio/true-peak compliance, and publication
provenance.

## Boundaries

- Do not renumber acts or alter the canonical running order.
- Do not invent missing copy or cast a person without evidence.
- Do not move an authored beat to satisfy a layout or gate constraint.
- Do not hand-edit derived fields, generated outputs, delivery digests, or
  files in `~/Videos/Wolves`.
- Do not delete dirty worktree files or remove a worktree until its branch is
  safely present on a remote.
- A reported gap, stale record, or blocked plate is recorded and degraded
  according to repository policy; it does not withhold the video. A failed
  artifact verification must be corrected before that artifact is published.

## Success criteria

- All authored work is either committed on a named, remotely reachable branch
  or explicitly left untouched with its disposition recorded.
- `release/alpha4` contains the alpha4 manifest and no unrelated changes.
- All stale acts are rebuilt from current release-branch inputs and published.
- The new megacut is assembled from the canonical 18-item plan and passes the
  required media and offline validation checks.
- The release branch is pushed and the final worktree/status audit is clean.
