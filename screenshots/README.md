# Screenshots

Static mockups + render utility. PNGs are gitignored — regenerate locally as needed.

## Files

| File | Purpose |
|---|---|
| `mockups.html` | Single HTML page with 8 scenes — architecture, card mock, platforms grid, Notion DB, Make scenario, cost log, niche rotation, Slack notifications |
| `render.py` | Playwright script that captures each scene into a PNG + a combined `all_screens.png` |
| `01_*.png` … `08_*.png` | Generated, gitignored |
| `all_screens.png` | Combined gallery (full-page screenshot), gitignored |
| `sample_*.png` | Live screenshots from real Make scenario, committed to git for the portfolio |

## Regenerate

```bash
pip install playwright
python -m playwright install chromium
python screenshots/render.py
```

To preview without rendering:

```bash
open screenshots/mockups.html        # macOS
xdg-open screenshots/mockups.html    # Linux
```
