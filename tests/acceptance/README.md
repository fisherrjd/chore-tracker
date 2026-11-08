# Acceptance tests

Black-box Playwright tests written by the software factory, one folder per run (`<run-id>/manifest.toml` lists each test and the source files it `covers`), with the sample data the app loads in `fixtures/<run-id>/`. Run them with the repo's `test:acceptance` script. The factory re-runs the ones a change can affect as a regression suite.
