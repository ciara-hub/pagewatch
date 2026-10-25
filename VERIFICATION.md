# Verification record

## Automated checks

Publication checks: **25 October 2026**.

The offline test suite contains **38 tests** using Python `unittest`. Graph responses are synthetic mocks; these checks do not access Facebook or real messages.

The suite covers Page identity and token checks, unavailable and partial data, retained caption baselines, explicit acceptance, inbound/outbound filtering, data minimization, exact hostname allowlisting, review rules, cursor pagination and the fixed GET-only transport.

~~~sh
python -m unittest discover -s tests -v
~~~

The [GitHub Actions workflow](.github/workflows/tests.yml) runs the automated checks on pushes and pull requests. The synthetic demo runs without Meta credentials and creates a separately labeled report.

## Live pilot

A separate pilot on **24 October 2026** read five Juhoonity posts, analyzed **69 API-visible comments**, and analyzed **16 inbound text messages** from one limited inbox sample.

See [the evaluation](docs/EVALUATION.md) for the per-post counts, timestamps, findings and API visibility limits. The pilot is not a measurement of detection accuracy or full Page coverage. Automated checks and real pilot data are reported separately.
