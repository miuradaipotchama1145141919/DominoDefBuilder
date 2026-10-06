# Domino module source schema

Domino sound source definitions are XML files. Domino's documented XML structure contains `ModuleData`, optional module options, `InstrumentList`, `DrumSetList`, `ControlChangeMacroList`, `TemplateList`, and `DefaultData`. Tags and attributes are case-insensitive, attribute order is not significant, and self-closing XML tags use the normal XML `/>` form.

DominoDefBuilder uses YAML as a maintainable source format and emits that XML. The `events` form is intentionally generic so a documented Domino event can be emitted without adding a special Python class for every event shape.

## module.yaml

```yaml
name: Device Name
folder: Manufacturer
priority: 100
creator: Author
version: "1.00"
website: ""
defaultCcmId: 7
exclusiveDefault: F0H 7EH 7FH 09H 03H F7H
rhythmGate: 10
previewDelay: 0
profiles:
  universal:
    header: F0H 7FH 7FH
    footer: F7H
```

`name` is required. `folder`, `priority`, `creator`, `version`, and `website` correspond to the documented `ModuleData` attributes. `priority` defaults to 100. Module options map to `ControlChangeEventDefault`, `ExclusiveEventDefault`, `RhythmTrackDefault`, and `ProgramChangeEventPropertyDlg`.

Profiles are a DominoDefBuilder convenience for composing repeatable SysEx headers and optional checksum wrapping. Raw `data` always takes precedence over a generated `sysex` block.

## voices.yaml

The emitted structure is `InstrumentList -> Map -> PC -> Bank`. Every PC needs at least one Bank in Domino, even for a device without a real bank system. PC numbers are 1 through 128. Bank `msb` and `lsb` are optional. Omitting either value means that Bank Select byte is not sent; 255 is also accepted by Domino as the no-send value.

```yaml
maps:
  - name: GM2 Bank 0
    start: 1
    names: [Piano, Piano 2]
    bank: {msb: 121, lsb: 0}
  - name: Extra
    programs:
      - pc: 9
        name: Voice
        banks:
          - {name: Voice A, msb: 121, lsb: 1}
          - {name: Voice B, msb: 121, lsb: 2}
```

The `start` and `names` fields are builder conveniences for repetitive sequential PC definitions. Explicit `programs` remain available for irregular maps.

## drums.yaml

`DrumSetList` follows the same Map, PC, and Bank structure, with `Tone` children on Banks. Tone `key` is 0 through 127. Shared tone lists can be named in `toneSets` and selected with `toneSet`.

```yaml
toneSets:
  kit:
    36: Kick
    38: Snare
maps:
  - name: Kits
    programs:
      - pc: 1
        name: Standard
        banks:
          - {name: Standard, msb: 120, lsb: 0, toneSet: kit}
```

## controls.yaml and effects.yaml

Both files contribute to `ControlChangeMacroList`. `controls.yaml` is merged before `effects.yaml`.

### Folders

A `folder` becomes a Domino `Folder`. Folders can be nested. Giving a folder an `id` makes it addressable by `FolderLink`.

```yaml
items:
  - type: folder
    id: 10
    name: Channel
    items: []
```

### CCM

A `ccm` becomes a `CCM`. Its supported fields are `id`, `name`, `color`, `sync`, `muteSync`, `value`, `gate`, `memo`, and `data` or `sysex`. Domino requires CCM IDs from 0 through 1300 and they must be unique. `Sync` may be omitted, `Last`, or `LastEachGate`. `MuteSync` is emitted as `1` when true.

### Value and Gate

`value` and `gate` use the same source shape. They map to the documented `Default`, `Min`, `Max`, `Offset`, `Name`, `Type`, and `TableID` attributes. `type: Key` exposes Domino's keyboard selector. `entries` creates inline `Entry` elements.

```yaml
value:
  default: 64
  min: -64
  max: 63
  offset: 64
  name: Position
  type: Key
  tableId: 2
  entries:
    - {label: Center, value: 0}
```

### Tables

A `table` can appear at the top level or inside a folder. It becomes a Domino `Table` and may be referenced from Value or Gate with `tableId`. Table IDs are non-negative and unique.

```yaml
tables:
  - id: 2
    entries:
      0: Center
      127: Full Right
```

### Links

`ccmLink` maps to `CCMLink` and can override Value and Gate defaults. `folderLink` maps to `FolderLink` and requires the target folder ID plus a display name; Value and Gate overrides are optional.

### Data

Domino documents these commands:

```text
@PB [HighValue] [LowValue]
@CP [Value]
@PKP [Key] [Value]
@CC [ControlChangeNumber] [Value]
@SYSEX F0H ..... F7H
@RPN [RPN MSB] [RPN LSB] [Data MSB] [Data LSB]
@NRPN [NRPN MSB] [NRPN LSB] [Data MSB] [Data LSB]
```

Commands and values are separated by spaces, and several commands may be chained in one Data string. Decimal fixed values, `1h` or `10H`, and `0x20` hexadecimal fixed values are accepted.

The documented dynamic tokens are `#NONE`, `#VL`, `#VH`, `#GL`, `#GH`, `#CH`, `#1CH`, `#2CH`, `#3CH`, `#PCH`, `#1RCH`, `#2RCH`, `#4RCH`, `#VF1`, `#VF2`, `#VF3`, `#VF4`, `#RSCTRT1`, `#RSCTRT1P`, `#RSCTRT2`, `#RSCTRT3`, `#RSCTPT1`, `#RSCTPT1P`, `#RSCTPT2`, `#RSCTPT3`, `#VPGL`, and `#VPGH`.

Square brackets inside `@SYSEX` delimit the checksum-covered region for Domino's automatic checksum insertion. The builder validates balanced brackets and preserves raw Data strings exactly. Checksum syntax must follow the target device's actual message specification.

## TemplateList

Templates bundle CC, PC, Comment, and Memo events for reuse. Templates can be placed inside folders.

```yaml
templates:
  - id: 0
    name: Channel Init
    events:
      - {tag: Memo, text: Init}
      - {tag: CC, attrs: {ID: 7, Value: 100}}
      - {tag: PC, attrs: {PC: 1, MSB: 121, LSB: 0, Mode: Auto}}
      - {tag: Comment, text: Normal channel}
```

## DefaultData

`DefaultData` defines the initial project content. Tracks are created in source order. The documented event types are `Mark`, `TimeSignature`, `KeySignature`, `CC`, `PC`, `Comment`, `Template`, and `EOT`. Track attributes are `Name`, `Ch`, `Mode`, and `Current`. `Mode` may be `Conductor` or `Rhythm`.

The builder supports a structured shorthand for common conductor fields and also supports generic event dictionaries for the complete documented event vocabulary:

```yaml
marks:
  - {meas: 2, name: Start}
conductorMarks:
  - {tick: 0, name: Setup}
tracks:
  - name: System Setup
    ch: 1
    events:
      - {tag: CC, attrs: {ID: 201, Value: 100, Tick: 0}}
  - name: Rhythm
    ch: 10
    mode: Rhythm
    events:
      - {tag: Template, attrs: {ID: 1, Tick: 480}}
```

Event `Tick` is an absolute position. Event `Step` controls the spacing used for subsequent placement when Domino interprets omitted Tick values. The builder preserves event attributes and text from the YAML `attrs` and `text` fields, so documented attributes can be used without a new schema field. An EOT is automatically added to a track that does not contain one.

For a useful real-world module, DefaultData should include a channel-1 System Setup track containing known global reset and startup defaults, grouped with comments such as Reset, Global, Effects, and CH Setup. Device-specific defaults must come from the device documentation or verified reference material rather than being invented.

A separate rhythm-channel Drum NRPN example track is appropriate when the device exposes per-note drum parameters through NRPN. Use the note number as Gate and place edits after any Program Change or other event that resets the drum parameters.

## Includes and loops

Every YAML source file is expanded before it is read. Expansion needs no extra dependency and the files stay valid YAML.

### include

`include` pulls in other YAML files. Paths are relative to the file that contains the include. Globs such as `voices/*.yaml` load in sorted order. Includes can nest, and circular includes are an error. Directories starting with an underscore are skipped when modules are discovered, so `_parts` is a good place for included files.

As a list item, `include` splices the items of the included list into the parent list.

```yaml
maps:
  - include: maps/*.yaml
```

As a mapping key, `include` merges the included mapping into the parent. Sibling keys override included keys. Merging is shallow.

```yaml
toneSets:
  include: toneSets/*.yaml
  extra: [...]
```

`with` passes variables to the included file. An included file whose content is a single `from: path` mapping is still supported and means the same as `include`.

### for

`for` repeats `do` once per item of `in`. It works in lists and wherever a value is expected. Results are spliced into the surrounding list. `in` is a list or `{range: [start, stop]}`, where stop is included. A third range value is the step.

```yaml
programs:
  - for: n
    in: {range: [1, 128]}
    do: {pc: "{n}", name: "Program {n}", banks: [{msb: 0, lsb: 0}]}
```

When an item of `in` is a mapping, its keys are also available as variables. The variable `index` is the zero based position. `for` loops can nest, and `in` can itself use `include`.

### Substitution

Inside a `for` or an include with `with`, text in braces is replaced by variables. Expressions support `+`, `-`, `*`, `//` and `%`, and a format after a colon, as in `{n:03}` or `{n + 1}`. A value that is only one placeholder keeps its number type. Names that are not variables are left as written. Substitution also applies to mapping keys and include paths. The key `for` is reserved.
