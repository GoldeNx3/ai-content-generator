# UI verification without OpenAI

`npm test` runs workflow and cost-label tests locally. No network access is needed.

For browser checks, start the built frontend with `npm run start -- --hostname 127.0.0.1 --port 3107`, then run `npm run test:ui`. The check requires Playwright and Chrome. If Playwright is available outside the project, set `PLAYWRIGHT_MODULE` to its absolute module path; `CHROME_PATH` optionally selects a Chrome executable.

The browser check intercepts **all** API requests, returns fixtures, and blocks other external requests. It never calls the real backend or OpenAI. It checks persistent fetch/batch results, partial errors, research polling, the generation gate, the paid-generation dialog, and mobile overflow. Set `UI_TEST_PORT=3000` to verify the deployed frontend with the same mocked API. The check also verifies shared headers/footers, classification accounting, separate brief/writer accounting, and aggregate research pricing. Screenshots are saved in `/tmp/content-*.png`.
