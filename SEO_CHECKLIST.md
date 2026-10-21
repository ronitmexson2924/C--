# SEO checklist for the C-- website

The code side of search-engine optimisation is done: every page has its own server-rendered URL,
metadata, structured data, and a sitemap. What remains are the steps only the site owner can take.
They are listed below in the order to do them.

## What the site already provides

| Item | Where |
|---|---|
| Six crawlable pages: `/`, `/playground`, `/architecture`, `/pipeline`, `/reference`, `/about` | `web/seo.py` (`PAGES`), `web/content/` |
| Unique `<title>`, meta description, canonical URL, Open Graph and Twitter tags per page | `web/seo.py` (`_head`) |
| JSON-LD: `WebSite`, `Organization`, `SoftwareApplication` (home), `TechArticle` (architecture, pipeline, reference), `FAQPage` (about), `BreadcrumbList` | `web/seo.py` (`structured_data`) |
| `/robots.txt`, `/sitemap.xml`, `/site.webmanifest`, `/favicon.ico`, apple-touch icon | `web/server.py`, `assets/` |
| 1200×630 social preview image | `assets/og-image.png` (regenerate with `python3 scripts/generate_seo_assets.py`) |
| Real HTTP 404s, 301s for `/index.html` and trailing slashes | `web/server.py` |
| gzip, ETags, long-lived cache for versioned CSS/JS, CSP and security headers, self-hosted fonts | `web/server.py`, `web/fonts/` |
| Automated checks for all of the above | `tests/test_web_seo.py` |

Lighthouse 13.5 (local server; scores are Performance / Accessibility / Best Practices / SEO):

| Page | Mobile | Desktop |
|---|---|---|
| `/` | 100 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/playground` | 99 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/architecture` | 100 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/pipeline` | 100 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/reference` | 97 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/about` | 98 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |

Production scores will differ slightly with network latency and the hosting region.

## 1. Deploy and set the public URL

1. Merge the changes and let Railway redeploy.
2. If you add a custom domain (strongly recommended, see step 5), set the `SITE_URL` environment
   variable in Railway to it, for example `https://cminusminus.dev`. Every canonical URL, Open Graph
   tag, JSON-LD block, and the sitemap use this value.
3. Check that these load in a browser:
   - `<your site>/robots.txt`
   - `<your site>/sitemap.xml`
   - `<your site>/reference` (view source: the content is in the HTML)

## 2. Google Search Console

1. Go to <https://search.google.com/search-console> and click **Add property**.
2. Choose **URL prefix** and enter the exact site URL, for example
   `https://web-production-c8ddc.up.railway.app/`.
3. Choose **HTML tag** verification. Copy only the `content` value from the tag Google shows,
   for example `abc123...`.
4. In Railway, add the environment variable `GOOGLE_SITE_VERIFICATION` with that value and redeploy.
   (Alternative: choose **HTML file** verification and set `GOOGLE_SITE_VERIFICATION_FILE` to the file
   name Google gives you, such as `google1234abcd.html`.)
5. Click **Verify** in Search Console.
6. Open **Sitemaps**, enter `sitemap.xml`, and click **Submit**.
7. Open **URL Inspection**, paste each page URL, and click **Request indexing**:
   `/`, `/playground`, `/architecture`, `/pipeline`, `/reference`, `/about`.
8. Check **Pages** and **Enhancements** after a few days for indexing status and structured-data
   reports. Fix anything flagged there.

## 3. Bing Webmaster Tools (also feeds DuckDuckGo and Yahoo)

1. Go to <https://www.bing.com/webmasters> and sign in.
2. Choose **Import from Google Search Console**. This copies the verified site and sitemap.
3. If you would rather verify directly, copy the `msvalidate.01` token, set it as
   `BING_SITE_VERIFICATION` in Railway, redeploy, and verify.

## 4. Validate the structured data

- <https://search.google.com/test/rich-results>: test `/`, `/reference`, and `/about`.
- <https://validator.schema.org>: paste any page URL.
- Social previews: <https://www.opengraph.xyz> or LinkedIn's Post Inspector.

## 5. Off-page work (this is what decides your ranking)

Search engines rank pages mostly on relevance plus the number and quality of sites linking to them.
A `railway.app` subdomain with no inbound links will be indexed, but it will not rank well until other
sites point to it.

1. **Custom domain.** Buy a short domain such as `cminusminus.dev`, attach it in Railway, set
   `SITE_URL`, and keep the Railway URL redirecting to it. Then add the new domain as a Search Console
   property and submit its sitemap.
2. **GitHub repository.**
   - Set the repository **Website** field to the site URL.
   - Add topics: `programming-language`, `compiler`, `memory-safety`, `transpiler`, `interpreter`, `python`.
   - Keep the README link to the live site at the top.
3. **Write-ups that link back.** Publish an article such as "Designing C--, a memory-safe C without
   pointers" on dev.to, Medium, or Hashnode, linking to the site and the repository.
4. **Communities.** Share it where people discuss languages, following each community's self-promotion
   rules: r/ProgrammingLanguages, r/Compilers, and a "Show HN" post on Hacker News.
5. **Academic and personal links.** Ask for the project to be listed on the department or university
   project showcase, and have each team member link to it from their GitHub profile README, LinkedIn,
   and portfolio.
6. **Language directories.** Add an entry to language indexes such as the Esolang wiki or Rosetta Code
   with a link to the site.

## 6. What to expect

- Google usually indexes a submitted site within a few days to a few weeks.
- Ranking is earned over weeks to months as links and visits accumulate. No code change can guarantee
  position 1. The site is set up to be eligible for the top result on specific searches, for example:
  - "C Minus Minus programming language"
  - "C-- memory safe language"
  - "C-- compiler explorer" / "C-- online playground"
  - "C-- to C99 transpiler"
  - "safety by removal programming language"
  - the team members' names together with "C--"
- The bare query "C--" is much harder. Search engines mostly drop the `--`, and the unrelated GHC
  intermediate language called C-- already holds those results. The site clarifies the difference
  on the home and about pages.

## Maintenance

- After changing page content, Search Console picks up the new `lastmod` from the sitemap
  automatically. Use **Request indexing** to speed up important updates.
- Page titles and descriptions live in `web/seo.py` (`PAGES`). Keep titles to 50–60 characters and
  descriptions to 140–160 characters; `tests/test_web_seo.py` enforces sensible limits.
- Run `python3 -m pytest tests/test_web_seo.py` before deploying.
