# Harazi Global Trading

Responsive static B2B sourcing website for Harazi General Trading Sdn. Bhd. Corporate details and sourcing qualifications are preserved from the existing site and supplied pages. `logo.png` is the approved logo already in the repository, used without alteration. Product illustrations represent sourcing categories, not inventory or authorized brands.

## Local development

No build step or application dependencies are required. From this checkout:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

The Python server serves pages and assets; it does not process inquiry submissions.

## Netlify deployment and forms

`netlify.toml` publishes the root directory without a build command. Deploy the PR branch for review; use `main` for production only after approval.

The `wholesale-inquiry` form uses a native POST, `data-netlify="true"`, a matching hidden `form-name`, named fields, a honeypot, required privacy acknowledgment and `/thank-you.html` as its success destination. JavaScript only handles navigation and category preselection; it does not intercept submission.

Before receiving real inquiries, enable form detection in the Netlify dashboard and redeploy. Confirm `wholesale-inquiry` appears in Forms, submit a test inquiry with non-sensitive data, verify the stored fields and success page, then configure and verify notifications. Browser tests mock the POST to check the client contract; they do not prove Netlify ingestion or email delivery.

Verified sales email and telephone were not supplied, so none have been invented. Legal drafts retain the supplied review requirements, including a dedicated privacy contact and Bahasa Malaysia privacy notice. Review these before public launch.

## Checks

The browser suite checks every page and asset, internal links, desktop/mobile layouts, keyboard navigation, mobile menu behavior, category preselection, required field validation and the form POST payload. Run with Python Playwright and Chromium available:

```sh
python3 tests/test_site.py
```

Set `CHROMIUM_PATH` if Chromium is not at `/usr/bin/chromium`. Tests start and stop their own local server and mock only the form submission endpoint. Test screenshots are written outside the checkout to `/tmp/harazi-screenshots`.
