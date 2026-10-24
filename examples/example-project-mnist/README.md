# example-project-mnist — seed bundle for the SciTeX example project

EXAMPLE DATA for SciTeX UI development (writer / live-paper /
agentic-journal panes). Not research findings: every number was
computed by `examples/make_example_project_mnist.py` — regenerate
with:

```
uv pip install scikit-learn matplotlib numpy  # generator-only deps
python examples/make_example_project_mnist.py
```

Hub side drops this directory into the `example-project-mnist`
user project; `/apps/live-paper/?working_dir=<this dir>` renders it.

```
example-project-mnist/
  manuscript.pdf   # 3-page demo paper (real MNIST images + computed figure)
  claims.json      # 3 claims carrying the computed accuracies
  dag.mmd          # fetch -> split -> train -> evaluate -> render
  provenance.yaml  # dataset, script, versions, seeds
  figz/            # accuracy + digit-sample PNGs (also in the PDF)
```
