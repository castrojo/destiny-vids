# Guardian nameplates

## When to Use

- Crediting a lead or the monthly ensemble on screen
- Changing plate copy, position, or timing
- Porting the Bluefin plate treatment somewhere new

## When NOT to Use

- Narration captions → the `authoring-video-closed-captions` skill
- Deciding *who* is cast → [`casting.md`](../casting/SKILL.md)

## The field set is closed

A Guardian nameplate carries **exactly**:

| Field | Example |
|---|---|
| `label` | `TRUSTEE // GUARDIAN` |
| `class` | `Voidwalker Warlock` |
| `name` | `Bob Killen` |
| `title` | `Reconciler of the Plane` |
| `trustee` | `true` — the burnished-silver chrome |

The deck's other shapes are the title card (`title`, `subtitle`, `body[]`) and
the **chat card** (`speaker`, `text`) —
[`references/conversation-cards.md`](references/conversation-cards.md).

Keep chat `text` verbatim. An owner-retired authored card remains complete in
the generator's `RETIRED` record, including timing and identity fields, and is
removed from active pass data; never preserve a partial duplicate.
When an owner requests a swear censor, use the Kubernetes helm only as an `o`
replacement: add a `censor` entry whose `find`
value occurs exactly once and whose `replace` value uses `{k8s}`.
`tools/plate.py` replaces that token with the cached official white helm; it
does not alter the authored source string. Use an asterisk for other letters,
and do not add censorship the owner did not request.

For owner-sequenced dialogue around a freeze, derive every window from the picture builder's evidenced constants, keep each card at `MIN_HOLD`, and regenerate the manifest; never hand-edit a generated plate clock. If review notes use a programme baseline, record the programme mark beside its baseline Act II film and source anchors, then derive the post-insert film time from the timeline shift. A source-attached cue must still resolve to the evidenced picture (including a held frame), not merely retain a stale film number. An external insert and its surrounding held frame are separate half-open intervals: raise inside the insert, and resolve the hold to its exact `source_at`.

### Cinematic text that shares the frame with identity plates

Owner-authored narration can use `kind: caption` in the top-safe rail while
Guardian and companion cards keep the lower third. Scene-setting metadata uses
`kind: context` above that lower-third lane; a full-screen deployment beat uses
`kind: warning`. These are independent chrome rows, not extra nameplate fields,
and each carries `copy_source: owner_supplied`.

A caption glyph replacement keeps the authored `text` unchanged and records the
mark under `glyphs`. The renderer reserves the mark's real width before wrapping
or centering, so a Kubernetes helm replacing one `o` cannot cover the next
letter. A missing mark degrades to the plain authored letter.

When one movement derivative burns more than one authored block,
`ending_derivative.overlay_section` may be an ordered list. The list is flattened
in order and all plate inputs are composed in one encode from the original
source; do not make one derivative per section or re-encode the clean movement.
FFmpeg documents this as a cascading complex overlay graph.
`source: /websites/ffmpeg_documentation, “Cascading Multiple Overlays”`

## Prose that is not written yet is lorem, never a gap

A chat pill with no `text` does **not** block and does not render empty:
`tools/placeholder.py` fills it with deterministic lorem ipsum, so timing,
seat and read length are reviewable while the copy is still being written.
`python3 tools/placeholder.py list` is the punch list.

**A placeholder credits nobody** — the vocab's uncast speaker (`TBD`) and the
drawn crest, never a real login or somebody's avatar; the intended speaker is
kept in `speaker_pending`. Lorem under a real name is still putting words in a
colleague's mouth, and act IV lost three people to exactly that. Details and
the named-badge distinction:
[`references/conversation-cards.md`](references/conversation-cards.md).

That is the whole vocabulary, taken from the reference deck
(`~/Videos/nameplates.json` —
[`references/copy-authoring.md`](references/copy-authoring.md)).
**Do not add a line the deck has no field for.**
An invented row — an `AS <CHARACTER>` casting line, a role, a pronoun — puts
unauthored text on a card whose entire purpose is naming real people, and a
test pins the vocabulary so it cannot drift by accident. If a plate genuinely
needs to say something new, add the field to the data model deliberately.

Local additions to the deck's shape are limited to chrome flags: `kind: ghost`
(drops the class line, because a Ghost has no subclass) and `variant` (`leader`
gold — the wolves trailer reserves it for Christoph Blecker — and it **takes
precedence over `trustee`**, mirroring the CSS selector
`.wolves-guardian-plate-trustee:not(.wolves-guardian-plate-leader)`, so a
binding may carry both flags and plate gold; the leader block does not restyle
the class row, which stays the default blue — and `rust`, oxidised iron for the
Rust Foundation herald, per #8 — and `bazzite`, Bazzite purple for the end
fight; `nobara`, indigo sampled from the Nobara Project's own icon; and
`youtube`, brand red for a creator whose affiliation is their channel). A

**A brand mark comes from the project's own site, never off this host.**
`scripts/fetch_brand_marks.py` caches them into gitignored `renders/marks/`,
and `/usr/share/pixmaps` is a trap that looks like the publisher's own
delivery: Bluefin **rebrands** it, so `fedora_whitelogo_med.png` and
`gnome-boot-logo.png` on this machine are both the Project Bluefin wordmark.
Act VIII's first pass credited "Fedora CoreOS" under a Bluefin logo because of
it, and only a rendered frame showed it. Prefer the **icon** over the
horizontal wordmark lockup too — a mark that spells the brand out cannot be
set small, and the owner's note on the first pass was *"you overdid the logos
those are tacky, smaller and symbolic."*

variant is colour only. Owner-authored imagery chrome — `avatar`,
`wreath`, bracketed names like `[ REDACTED ]` — is likewise not copy:
[`references/plate-chrome.md`](references/plate-chrome.md).

A banner may use `position: "letterbox-top"` to center against the measured
picture and seat in the top matte without adding another banner renderer.

The deck's `gp_*` entries add three **placement** fields, which are deck data,
not new copy: `position: "group"` with an absolute `x` (measured against the
picture, never the raw frame), a `scale` that shrinks the card, and a `group`
key marking which row a card belongs to. Two more come from the intro overlay:
`raised` (`top: 28%`, for a Guardian towering over the lower third) and
`position: "status"`.

## Core Process

```bash
python3 tools/ensemble.py roster --month YYYY-MM --out roster.json
python3 tools/plate.py plan cut.json --roster roster.json --max-shot-sec 9 \
    --out plates.json
python3 tools/plate.py burn --video renders/cut.mp4 --manifest plates.json \
    --out renders/cut-plated.mp4
```

A dense schedule must still end in **one picture encode**. If the burn grows to
so many independent still inputs that FFmpeg spends its time building scaler
graphs instead of emitting frames, composite the already-rendered full-frame
RGBA plates at their manifest boundaries into one alpha-preserving overlay
stream, then overlay that stream onto the clean act once. Do not split the deck
across successive lossy burns. FFmpeg's `overlay` filter accepts an alpha input
and supports straight, premultiplied, or automatic alpha handling.
`source: /websites/ffmpeg_documentation, “overlay”`

## Burn on the main stream's frame grid

`tools/plate.py burn` expresses every overlay window with FFmpeg's timeline
`enable` expression using `n`, the output frame count, and a half-open
`gte(n,start)*lt(n,end)` window. It probes the main video stream's
`r_frame_rate` and ceils both boundaries on that grid: decimal seconds such as
`46.596550` are frame boundaries, and rounding them to milliseconds can move the
first visible frame late. Do not assume the delivery rate: an Act II base at
30 fps must show a `1.0`–`3.0` plate on frames 30 through 89. The half-open upper
bound is deliberate: when adjacent overlays meet, the later overlay owns its
first frame. FFmpeg's timeline evaluator supplies both `n` and `t` per frame and
treats a non-zero expression as enabled.
`source: /websites/ffmpeg_doxygen_8_0, “Evaluate Timeline Expression”`

A burn-path regression test must use the resolved local H.264 encoder, synthetic
`60000/1001` and 30 fps sources, and decoded frames on both sides of each
boundary. Skip only when the resolver cannot provide H.264 encode/decode; a
mocked argv does not prove a pixel landed. Farm runners must replace any local
container resolver prefix with native remote `ffmpeg` before submission.

`plan` reads copy from `vocab/casting.yaml`'s `plate:` block — the same file
that binds a character to a person — so recasting a role changes the on-screen
credit and nothing else.

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`copy-authoring.md`](references/copy-authoring.md) | **Read before writing any copy.** The four files that author identities, the ten authored people, and the known divergences. |
| [`from-a-brief.md`](references/from-a-brief.md) | Issue `brief` block → roster → planned manifest → burned cut, and the ordering rules. |
| [`conversation-cards.md`](references/conversation-cards.md) | The kinds that own their own row (`status`, `miniboss`, `achievement`, `companion`) and the `chat` card. |
| [`placement-and-styling.md`](references/placement-and-styling.md) | Letterbox-safe placement, and where the treatment is ported from. |
| [`plate-chrome.md`](references/plate-chrome.md) | `avatar`, `wreath`, bracketed names — imagery, not copy. |
| [`plate-styling.md`](references/plate-styling.md) | Constant-by-constant CSS provenance and the font trap. |
| [`status-nameplate.md`](references/status-nameplate.md) | The top-of-frame HUD card. |
| [`other-cards.md`](references/other-cards.md) | `miniboss`, `achievement`, `companion` detail. |
| [`full-frame-cards.md`](references/full-frame-cards.md) | `act` and `comic` — rendered by the website's own CSS, not Pillow. |
| [`hero-credit.md`](references/hero-credit.md) | Act VIII's cast placard — a lower third that credits the person, not the character. |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "One extra line makes the plate clearer." | It makes the plate say something nobody wrote. The deck's fields are the contract. |
| "I'll hardcode the copy just for this render." | Then the credit and the casting drift apart the first time a role is recast. Copy lives in `vocab/casting.yaml` — or, for someone the vocab does not bind yet, in the issue's brief, which `plan` marks `copy_source: brief`. |
| "The brief's copy contradicts the binding, but the owner wrote it today." | Recency is not authority: the vocab is the reviewed record, the issue body is editable. The vocab wins; edit it if the brief is right. |
| "I'll hand-author the manifest, so `plan`'s rules don't apply." | They still apply — `plan` was just the only thing enforcing them. `render` and `burn` now run `check_copy_against_bindings`, and a card contradicting its binding is refused unless it carries a `copy_override` naming the deciding issue. |
| "The plate is short, it can share the screen." | Two plates at once is unreadable; both `plan` and `burn` refuse it. The only exception is a group row, whose members are built to be seen together. |
| "The shot is only two seconds, so nobody can be plated there." | The plate rides across the cut. Only the *anchor* must be long enough to register. |
| "I'll put a plausible name on the placeholder so it looks finished." | A plate names a real person. `TBD` is the honest answer until a roster exists. |
| "No copy for this lead? Write them something." | Then the plate says what nobody wrote. Leave them in `unresolved` until the owner writes it. |

## Red Flags

- Inventing a plate line, a role, or a pronoun row — from a brief same as
  anywhere else: `plan` refuses a `copy` field outside the deck's set.
- Hardcoding copy in the manifest instead of `vocab/casting.yaml`.
- A plate manifest that hides where its copy came from — every planned entry
  carries `copy_source`, and a brief plate without it is a hand-edit.
- Letting a brief override a binding's `plate:` block silently. The vocab
  wins; if the brief is right, the fix is a vocab edit, not a per-video
  override.
- Calling a burn done because ffmpeg exited 0. Check a frame, not the manifest.
- Guessing a pill's seat when the manifest's clock is in doubt. Omission
  degrades, misplacement lies: a pill that cannot be placed on evidence is
  omitted and recorded in `unresolved`, and the act ships with fewer pills.
  Never hold the film — and never ship the old master instead, because stale
  copy on screen is the same fault as misplaced copy with an older timestamp.
- **Deck colours on a card that sits over MOVING PICTURE.** The deck's greys
  (`--wc-grey` #8b8f96, and the secondary #cbd5e1) are chosen against a slide's
  black. Over footage they hold for as long as the shot is dark and vanish the
  moment it is not. Measure the luma across the card's own window
  (`signalstats` → `YAVG`) instead of judging it on the frame you cued to: the
  prologue's main title was cued over a near-black void and the source cut to a
  white starburst 1.3 s later, inside the same card.
- **Protecting that type with a panel behind it.** A scrim is the right
  diagnosis and the wrong object — over moving picture it reads as a box,
  because it is one, and the owner will say so. Put the protection on the
  **glyphs**: a tight near-opaque core plus wider soft falloffs travels with
  the letterforms and has no edge of its own. `act.html`'s radial wash is for
  a slide, where nothing is behind it.
- **A looped still overlaid on a finite picture, without a bound.**
  `loop=loop=-1` is an INFINITE stream, and `overlay`'s framesync keeps
  producing output after the *main* input ends, repeating its last frame.
  The prologue's first build emitted the film and then eight seconds of frozen
  final frame, the material after it never played, and ffmpeg exited 0. `trim`
  the still to the picture's length and add `shortest=1`. It was caught by
  pulling three frames and noticing they were identical — not by watching.
- Shipping a cut with a non-empty `unresolved` list without reading it: someone
  who was on screen went uncredited. The list is the whole punch-list — an
  empty `unresolved` really does mean nobody was missed, so anything it does
  not report is a bug in `plan`, not a gap to work around.
- Planning with a different `--max-shot-sec` than the render used — every plate
  after the first trimmed shot lands late.
- A subclass line on a Ghost.
- A plate rendered in Adwaita Mono (or anything but DejaVu Sans Mono) — it is
  not in the font stack and matches none of the other videos.
- Styling taken from the live site where the baked reveal disagrees.
- A full-frame card re-implemented in Python instead of rendered from the
  site's CSS — that is a second copy of chrome that already exists, and the two
  drift the first time the site changes.
- Falling back to `Bluefin Blueberry` for one of the seven people whose
  Guardian identity **is** authored (see "Where the copy is authored"). An
  unknown seal is a blueberry; a known one is a paraphrase.
- A plate positioned against the frame on a letterboxed source, so it sits on
  the black bar instead of the picture.
- A placeholder plate carrying anything but the vocab's uncast copy, or shipping
  alongside a real roster.

## When a card must diverge from its binding

Only with an explicit, greppable record. `render` and `burn` call
`check_copy_against_bindings`, which refuses any card whose `name` matches an
authored identity but whose `label`/`class`/`title` do not — unless it carries:

```json
"copy_override": {
  "reason": "owner brief 2026-08-13 contradicts the committed binding",
  "binding": "cayde_6",
  "decided_by": "https://github.com/castrojo/destiny-vids/issues/111"
}
```

`decided_by` is required, so the escape hatch cannot be taken by accident and
always names who is settling it. An override is a **recorded violation with an
owner on the hook**, not a second way to be right — act VI's tail is the worked
example, and its two cards exist to be resolved, not copied.

## Verification

```bash
python3 -m pytest -q tests/test_plate.py     # includes the closed-vocabulary test
python3 -m pytest -q tests/test_derive.py    # pins every authored plate verbatim

# diff every binding against the file that authored it (read-only) --
# the snippet lives in references/plate-styling.md, "Checking a binding for drift"

# eyeball a plate inside its window
ffmpeg -ss <at+1> -i renders/cut-plated.mp4 -frames:v 1 /var/tmp/plate.jpg
```
