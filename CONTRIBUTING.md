# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using `mise run lint`).
4. Test you contribution.
5. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [black](https://github.com/ambv/black) to make sure the code follows the style.

## Test your code modification

This custom component is based on [integration_blueprint template](https://github.com/ludeeus/integration_blueprint).

It comes with development environment in a container, easy to launch
if you use Visual Studio Code. With this container you will have a stand alone
Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml)
file.

### Unit tests

```bash
mise run test
```

`tests/test_integration.py` runs the integration on an in-process Home
Assistant from
[pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component),
with HA's HTTP client mocked to serve `sample_pages/`. These tests are fast
and need no Docker, but nothing goes over a real network.

### End-to-end tests

`tests/e2e/` runs the integration the way it runs for real: Home Assistant
(the official container image) with `custom_components/` mounted, polling a
fake Servicewelt portal in a second container that serves the captured pages
in [`sample_pages/`](./sample_pages). Inside the compose network the fake
portal answers at `http://servicewelt`, the same hostname as the real device.
The tests onboard a fresh HA, add the integration through the config flow
over HA's REST API, and check entity states. They also change pages, break
them and slow them down through the fake portal's `/_control` API.

Docker is required. Each session starts from a clean HA:

```bash
mise run test-e2e
```

- `E2E_NO_BUILD=1` skips rebuilding the fake portal image.
- `E2E_KEEP_STACK=1` leaves the containers up afterwards. HA is at
  <http://localhost:18123> (user `e2e`, password `e2e-password`) and the fake
  portal is at <http://localhost:18080/?s=1,0>.
- `HA_VERSION` picks a different Home Assistant image tag.
- `HA_PORT` and `PORTAL_PORT` change the host ports.
- The HA log from the last run is written to `tests/e2e/logs/homeassistant.log`.

To capture a new portal page, save it as `sample_pages/s_<a>_<b>.html` (for
`?s=<a>,<b>`). The fake portal serves it without any other changes.

### HACS and Home Assistant validation

The `Validate` workflow runs both checks below; they can also run locally with Docker:

```bash
mise run validate-hassfest
```

```bash
GITHUB_TOKEN=<token> mise run validate-hacs
```

`validate-hacs` checks the repository as published on GitHub (its description,
topics and default branch), not your local checkout, so push first.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
