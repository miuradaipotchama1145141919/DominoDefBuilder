def scaffoldFiles(vendor, model):
    return {
        "module.yaml": 'name: %s %s\nfolder: %s\npriority: 100\ncreator: ""\nversion: "1.00"\nwebsite: ""\n'
        % (vendor.title(), model.upper(), vendor.title()),
        "voices.yaml": "maps:\n  - name: 001-002 Example\n    start: 1\n    names: [Example One, Example Two]\n",
        "drums.yaml": "toneSets:\n  example:\n    36: Kick\n    38: Snare\nmaps:\n  - name: Kits\n    programs:\n      - pc: 1\n        name: Example Kit\n        banks:\n          - toneSet: example\n",
        "controls.yaml": 'items:\n  - type: folder\n    name: Channel\n    items:\n      - type: ccm\n        id: 7\n        name: Volume\n        value: {default: 100, min: 0, max: 127}\n        data: "@CC 7 #VL"\n',
        "effects.yaml": "items: []\n",
        "defaults.yaml": 'tempo: 120\ntimeSignature: "4/4"\n',
    }
