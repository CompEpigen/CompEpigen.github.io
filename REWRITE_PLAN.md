# Website rewrite plan

## Goals
- Keep the lab site as a **single-page dashboard**.
- Make it **mobile-friendly**, readable, and easy to update.
- Preserve compatibility with **GitHub Pages** by using plain static files.
- Retain the existing core content: research, team, software, publications, positions, and contact details.

## Architecture
- `index.html`: semantic single-page structure.
- `assets/styles.css`: responsive layout and design system.
- `assets/script.js`: lightweight mobile navigation and dynamic footer year.
- Existing folders such as `img/` and `methrix/` remain hostable on GitHub Pages.

## Design changes
- Replace the dense dashboard grid with a **hero + section cards** layout.
- Add a **sticky top navigation** with anchor links.
- Use **responsive CSS Grid** so the page collapses cleanly on tablets and phones.
- Improve hierarchy through spacing, typography, and consistent card styles.
- Convert obfuscated email text into a clickable `mailto:` link.

## Content strategy
- Keep the site concise.
- Present software as grouped link clusters.
- Split team members by affiliation while keeping everything on one page.
- Reserve a simple alumni area that can be expanded later.

## Maintenance recommendations
- Store editable content close to the relevant section in `index.html`.
- For later improvements, consider moving people/software entries into a small JSON or JS data file.
- Periodically verify external links and job postings.
