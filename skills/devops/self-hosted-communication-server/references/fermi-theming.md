# Fermi Theming — Discord-Exact Colors

Fermi uses CSS variables in `themes.css` for theming. Colors are defined in
`.Dark-theme` and `.no-theme` blocks. The file is at `/opt/fermi/dist/webpage/themes.css`
on the VPS.

## Discord-Exact Dark Theme

Replace the `.Dark-theme` / `.no-theme` CSS blocks with these exact Discord hex codes:

```css
.Dark-theme, .no-theme {
    color-scheme: dark;
    --primary-bg: #313338;              /* Discord dark background */
    --primary-hover: #2b2d31;           /* slightly darker hover */
    --primary-text: #dbdee1;            /* main text color */
    --primary-text-soft: #949ba4;       /* secondary/muted text */
    --secondary-bg: #111214;            /* deepest background (dock, modals) */
    --secondary-hover: #1e1f22;         /* hover on secondary */
    --servers-bg: #1e1f22;              /* server list sidebar */
    --channels-bg: #2b2d31;             /* channel list sidebar */
    --channel-selected: #3f4147;        /* selected channel highlight */
    --typebox-bg: #383a40;              /* message input box */
    --button-bg: #4e5058;               /* button background */
    --button-hover: #6d6f78;            /* button hover */
    --spoiler-bg: #000000;
    --link: #00a8fc;                    /* Discord link blue */
    --primary-text-prominent: #f2f3f5;  /* bright/header text */
    --dock-bg: #111214;
    --card-bg: #111214;
    --accent-color: #5865F2;            /* Discord blurple */
    --primary-button-bg: color-mix(in srgb, #777777 10%, #5865F2);
}
```

## Deployment

CSS changes in `dist/webpage/` take effect immediately (no server restart needed,
unlike `instances.json` changes).

Always update BOTH directories:
```bash
# dist/ is live, src/ is the rebuild source
# Edit dist/ for immediate effect
vim /opt/fermi/dist/webpage/themes.css

# Then copy to src/ for persistence across rebuilds
cp /opt/fermi/dist/webpage/themes.css /opt/fermi/src/webpage/themes.css
```

## Variables Reference

| Variable | Purpose |
|----------|---------|
| `--primary-bg` | Main chat area background |
| `--primary-text` | Default message text |
| `--primary-text-soft` | Muted/secondary text (timestamps, etc.) |
| `--channels-bg` | Left sidebar channel list |
| `--servers-bg` | Server/guild list column |
| `--typebox-bg` | Message input area |
| `--accent-color` | Accent/blurple |
| `--link` | Hyperlink color |
| `--channel-selected` | Highlighted/active channel |
| `--primary-hover` | Hover state for main elements |
| `--button-bg` | Default button background |
| `--button-hover` | Button hover state |
